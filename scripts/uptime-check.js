#!/usr/bin/env node
/**
 * Site Uptime Monitor — Node.js version. Checks all client sites, logs results.
 */
const fs = require("fs");
const path = require("path");
const https = require("https");
const http = require("http");

const SITES_FILE = path.join(__dirname, "sites.json");

function checkSite(site) {
  return new Promise((resolve) => {
    const url = new URL(site.url);
    const lib = url.protocol === "https:" ? https : http;
    const start = Date.now();
    
    const req = lib.get(url, { timeout: 15000, headers: { "User-Agent": "AgencyMonitor/1.0" } }, (res) => {
      const ms = Date.now() - start;
      let body = "";
      res.on("data", (c) => body += c);
      res.on("end", () => resolve({
        name: site.name, url: site.url, status: res.statusCode, ms,
        ok: res.statusCode >= 200 && res.statusCode < 400,
      }));
    });
    
    req.on("error", (err) => resolve({
      name: site.name, url: site.url, status: 0, ms: Date.now() - start,
      ok: false, error: err.message.slice(0, 200),
    }));
    
    req.on("timeout", () => {
      req.destroy();
      resolve({ name: site.name, url: site.url, status: 0, ms: Date.now() - start, ok: false, error: "timeout" });
    });
  });
}

async function main() {
  if (!fs.existsSync(SITES_FILE)) {
    console.log(JSON.stringify({ status: "no_sites_file" }));
    process.exit(0);
  }

  const sites = JSON.parse(fs.readFileSync(SITES_FILE, "utf-8"));
  const results = [];

  for (const site of sites) {
    const r = await checkSite(site);
    results.push(r);
    process.stderr.write(r.ok ? "." : "x");
  }
  process.stderr.write("\n");

  const ok = results.filter((r) => r.ok).length;
  const failures = results.filter((r) => !r.ok);
  const report = { timestamp: new Date().toISOString(), total: results.length, ok, failures: failures.length, results };
  console.log(JSON.stringify(report, null, 2));
  if (failures.length) process.exit(1);
}

main().catch((err) => { console.error(err.message); process.exit(1); });
