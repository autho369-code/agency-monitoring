#!/usr/bin/env python3
"""
Site Uptime Monitor — runs every 30 min via cron.
Checks all client sites, logs results, sends Discord alerts on failures.
Reads site list from sites.json in same directory.
"""
import json, os, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SITES_FILE = os.path.join(SCRIPT_DIR, "sites.json")
DISCORD_WEBHOOK = os.environ.get("DISCORD_MONITORING_WEBHOOK", "")

def load_sites():
    if not os.path.exists(SITES_FILE):
        print(json.dumps({"status": "no_sites_file", "message": f"Create {SITES_FILE} with [{\"url\": \"...\", \"name\": \"...\"}]"}))
        sys.exit(0)
    with open(SITES_FILE) as f:
        return json.load(f)

def check_site(site):
    url = site["url"]
    name = site.get("name", url)
    start = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgencyMonitor/1.0"})
        res = urllib.request.urlopen(req, timeout=15)
        ms = int((time.time() - start) * 1000)
        return {"name": name, "url": url, "status": res.status, "ms": ms, "ok": 200 <= res.status < 400}
    except Exception as e:
        ms = int((time.time() - start) * 1000)
        return {"name": name, "url": url, "status": 0, "ms": ms, "ok": False, "error": str(e)[:200]}

def send_discord_alert(failures):
    if not DISCORD_WEBHOOK:
        return
    lines = [f"🔴 **{len(failures)} site(s) down** — {datetime.now(timezone.utc).strftime('%H:%M UTC')}"]
    for f in failures:
        err = f.get("error", f"HTTP {f['status']}")
        lines.append(f"• **{f['name']}** — {err} ({f['ms']}ms)")
    
    data = json.dumps({"content": "\n".join(lines)}).encode()
    req = urllib.request.Request(DISCORD_WEBHOOK, data=data, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10)

def main():
    sites = load_sites()
    results = []
    for site in sites:
        r = check_site(site)
        results.append(r)
    
    ok = sum(1 for r in results if r["ok"])
    failures = [r for r in results if not r["ok"]]
    
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "ok": ok,
        "failures": len(failures),
        "results": results,
    }
    
    print(json.dumps(report, indent=2))
    
    if failures:
        send_discord_alert(failures)
        sys.exit(1)

if __name__ == "__main__":
    main()
