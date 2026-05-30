#!/usr/bin/env python3
"""
SSL Certificate Expiry Check — runs weekly.
Checks SSL certs for all client domains, alerts if expiring within 30 days.
"""
import json, os, sys, ssl, socket, datetime
from datetime import timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SITES_FILE = os.path.join(SCRIPT_DIR, "sites.json")
DISCORD_WEBHOOK = os.environ.get("DISCORD_MONITORING_WEBHOOK", "")
WARN_DAYS = 30

def get_cert_expiry(hostname):
    """Get SSL cert expiry date for a hostname."""
    ctx = ssl.create_default_context()
    with socket.create_connection((hostname, 443), timeout=10) as sock:
        with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
            cert = ssock.getpeercert()
            expiry_str = cert["notAfter"]
            # Parse ASN.1 format: "Mar 15 12:00:00 2026 GMT"
            return datetime.datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)

def main():
    if not os.path.exists(SITES_FILE):
        print(json.dumps({"status": "no_sites_file"}))
        sys.exit(0)
    
    with open(SITES_FILE) as f:
        sites = json.load(f)
    
    results = []
    today = datetime.now(timezone.utc)
    
    for site in sites:
        hostname = site["url"].replace("https://", "").replace("http://", "").split("/")[0]
        try:
            expiry = get_cert_expiry(hostname)
            days_left = (expiry - today).days
            warning = days_left <= WARN_DAYS
            results.append({
                "name": site.get("name", hostname),
                "hostname": hostname,
                "expires": expiry.isoformat(),
                "days_left": days_left,
                "warning": warning,
            })
        except Exception as e:
            results.append({
                "name": site.get("name", hostname),
                "hostname": hostname,
                "error": str(e)[:200],
            })
    
    warnings = [r for r in results if r.get("warning")]
    
    print(json.dumps({"timestamp": today.isoformat(), "checked": len(results), "warnings": len(warnings), "results": results}, indent=2, default=str))
    
    if warnings and DISCORD_WEBHOOK:
        import urllib.request
        lines = [f"🔒 **SSL expiring soon** — {len(warnings)} cert(s)"]
        for w in warnings:
            lines.append(f"• **{w['name']}** — {w['days_left']} days left (expires {w['expires'][:10]})")
        data = json.dumps({"content": "\n".join(lines)}).encode()
        req = urllib.request.Request(DISCORD_WEBHOOK, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)

if __name__ == "__main__":
    main()
