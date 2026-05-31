#!/usr/bin/env node
/**
 * Stockbit Token Server
 * Listens on localhost:3002 for token updates from the Chrome extension.
 * Writes the new token to config.json automatically.
 *
 * Run once: node token-server.js
 * Keep running in a terminal tab. The extension will push tokens to it.
 */

const http = require("http");
const fs   = require("fs");
const path = require("path");

const PORT       = 3002;
const CONFIG     = path.join(__dirname, "config.json");

const server = http.createServer((req, res) => {
  // CORS for Chrome extension
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    res.writeHead(204); res.end(); return;
  }

  if (req.method === "GET" && req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  if (req.method === "POST" && req.url === "/token") {
    let body = "";
    req.on("data", c => body += c);
    req.on("end", () => {
      try {
        const { token } = JSON.parse(body);
        if (!token || typeof token !== "string") throw new Error("Invalid token");

        const cfg = fs.existsSync(CONFIG)
          ? JSON.parse(fs.readFileSync(CONFIG, "utf8"))
          : {};

        cfg.bearer_token = token;
        fs.writeFileSync(CONFIG, JSON.stringify(cfg, null, 2));

        const preview = token.slice(0, 20) + "…";
        const ts = new Date().toLocaleTimeString("id-ID");
        console.log(`[${ts}] ✓ Token updated: ${preview}`);

        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true }));
      } catch (err) {
        console.error("Error updating token:", err.message);
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: false, error: err.message }));
      }
    });
    return;
  }

  res.writeHead(404); res.end();
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`Stockbit Token Server running on localhost:${PORT}`);
  console.log(`Waiting for token from Chrome extension…`);
});
