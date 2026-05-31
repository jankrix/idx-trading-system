# IDX Swing Trading System — Setup Guide

This file is the single source of truth for replicating the full trading system on a new machine.
Read this first before touching any other file.

---

## System Overview

Five components work together:

```
TradingView Desktop ──CDP──► TradingView MCP ──► Claude Code
                                                       │
Stockbit Web ──token──► Chrome Extension               │
                              │                        │
                         Token Server ──config.json──► Stockbit MCP ──►┘
```

| Component | What it does | Required? |
|-----------|-------------|-----------|
| **Claude Code** | The AI agent that runs the morning/evening analysis | Yes |
| **TradingView Desktop** | Charting app — Claude controls it via CDP | Yes |
| **TradingView MCP** | Node.js bridge between Claude and TradingView Desktop | Yes |
| **Stockbit MCP** | Node.js server that fetches broker flow data from Stockbit API | Yes |
| **Token Server** | Tiny HTTP server that receives token from Chrome extension | Yes |
| **Chrome Extension** | Auto-captures Bearer token from Stockbit, syncs to config.json | Recommended |
| **News MCP (Tavily)** | Web news search via Tavily API | Yes |

---

## Prerequisites

- macOS (the launchd auto-start is macOS-specific; see VPS section for Linux)
- Node.js ≥ 18 (`node --version`)
- npm ≥ 8 (`npm --version`)
- Google Chrome
- TradingView account (free tier works)
- Stockbit account (for broker flow data)
- Tavily API key (for news search — free tier available at tavily.com)

---

## Step 1 — Clone / Copy the Project

```bash
git clone https://github.com/REPO_URL/idx-trading-system.git
cd idx-trading-system
```

The repo contains two folders:
```
idx-trading-system/
├── (root)          ← Pine scripts, workflow guides, CLAUDE.md (this folder)
└── stockbit-mcp/  ← Stockbit MCP server + Chrome extension
```

Also needed separately (see Step 2):
```
~/tradingview-mcp/  ← TradingView MCP server
```

---

## Step 2 — TradingView MCP

This MCP controls TradingView Desktop via Chrome DevTools Protocol (CDP).

**Source:** https://github.com/your-tradingview-mcp-repo (or copy from existing machine)

```bash
# Install dependencies
cd ~/tradingview-mcp
npm install

# Verify it works
node src/server.js --help
```

**How it connects:** TradingView Desktop exposes a CDP port. The MCP connects to that port and controls the app via JavaScript injection. No API key needed — just the desktop app running.

**TradingView Desktop must be running** before Claude can use the MCP.

---

## Step 3 — Stockbit MCP

```bash
cd idx-trading-system/stockbit-mcp
npm install
```

**Test it works:**
```bash
node -e "const h=require('https'); h.get('https://exodus.stockbit.com/order-trade/running-trade?symbols[]=BBCA&sort=DESC&limit=1&order_by=RUNNING_TRADE_ORDER_BY_TIME', {headers:{Authorization:'Bearer '+require('./config.json').bearer_token}}, r=>{let d=''; r.on('data',c=>d+=c); r.on('end',()=>console.log(JSON.parse(d).message))}).on('error',e=>console.error(e))"
```

Expected: `Successfully loaded running trade data`
If you get 401: token expired — do Step 6 (token refresh).

**Three tools Claude uses:**

| Tool | What it returns |
|------|----------------|
| `stockbit_broker_distribution` | Full-day broker net buy/sell, foreign flow, dominant Bandar. **Primary tool.** |
| `stockbit_delta_summary` | Open session vs close session delta (200 sampled trades) |
| `stockbit_running_trade` | Raw tick data — for deep inspection only |

---

## Step 4 — Token Server (auto-start on login)

The token server receives the Stockbit Bearer token from the Chrome extension and writes it to `config.json`.

**Start it once manually to test:**
```bash
cd idx-trading-system/stockbit-mcp
node token-server.js
# Should print: Stockbit Token Server running on localhost:3002
```

**Install as a macOS launchd service (auto-starts on login, auto-restarts on crash):**

Create `~/Library/LaunchAgents/com.USERNAME.stockbit-token-server.plist` — replace `USERNAME`, `YOUR_NODE_PATH`, and `YOUR_PROJECT_PATH`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.USERNAME.stockbit-token-server</string>
    <key>ProgramArguments</key>
    <array>
        <string>YOUR_NODE_PATH</string>
        <string>YOUR_PROJECT_PATH/stockbit-mcp/token-server.js</string>
    </array>
    <key>WorkingDirectory</key>
    <string>YOUR_PROJECT_PATH/stockbit-mcp</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/USERNAME/Library/Logs/stockbit-token-server.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/USERNAME/Library/Logs/stockbit-token-server.log</string>
</dict>
</plist>
```

Find your node path with: `which node`
Find your project path with: `pwd` inside the stockbit-mcp folder

```bash
# Load the service
launchctl load ~/Library/LaunchAgents/com.USERNAME.stockbit-token-server.plist

# Verify running
curl -s http://localhost:3002/health   # → {"ok":true}

# View logs
tail -f ~/Library/Logs/stockbit-token-server.log
```

**Manage the service:**
```bash
launchctl unload ~/Library/LaunchAgents/com.USERNAME.stockbit-token-server.plist  # Stop
launchctl load   ~/Library/LaunchAgents/com.USERNAME.stockbit-token-server.plist  # Start
```

---

## Step 5 — Chrome Extension

The extension auto-captures the Bearer token whenever Stockbit loads, then lets you sync it to `config.json` with one click.

**Install:**
1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked**
4. Select: `stockbit-mcp/extension/` folder
5. The extension icon appears in toolbar

**How it works:**
- Background script intercepts every request to `exodus.stockbit.com` and captures the Authorization header
- Token is stored in Chrome's local storage
- Clicking the popup → **Sync Token to Claude** → POSTs to `localhost:3002` → token written to `config.json`

**If the extension doesn't load:** check `chrome://extensions` for error messages. The manifest.json references no icon file (removed), so it should load cleanly.

---

## Step 6 — Daily Token Refresh (30 seconds)

The Stockbit Bearer token expires every 24 hours.

**Daily routine (do once before morning scan):**
1. Open Stockbit at `stockbit.com` in Chrome (just needs to load any page)
2. Click the **Stockbit Token Sync** extension icon in toolbar
3. Verify "Token captured: Yes" is shown
4. Click **Sync Token to Claude**
5. You'll see "✓ Token saved to config.json"

**If you see 401 errors** from the Stockbit MCP tools: token expired. Repeat the 5 steps above.

**Manual fallback** (if extension isn't installed):
1. Open stockbit.com in Chrome
2. F12 → Network tab → click any request to `exodus.stockbit.com`
3. Copy the `Authorization: Bearer eyJ...` header value (just the token part)
4. Paste into `stockbit-mcp/config.json`:
   ```json
   { "bearer_token": "eyJ..." }
   ```

---

## Step 7 — News MCP (Tavily)

Used by Claude to search news for each ticker during morning/evening scans.

**No installation needed** — it uses `npx` and downloads automatically.

**Requires a Tavily API key.** Get one free at https://tavily.com

The API key is stored in `~/.claude.json` under `mcpServers.news-search.env.TAVILY_API_KEY`.

---

## Step 8 — Register All MCPs in Claude Code

Claude Code reads MCP server configs from `~/.claude.json`. On a new machine, add all three servers:

```bash
# Open the file
nano ~/.claude.json
```

Add under `"mcpServers"`:

```json
{
  "mcpServers": {
    "tradingview": {
      "type": "stdio",
      "command": "node",
      "args": ["/Users/YOUR_USER/tradingview-mcp/src/server.js"],
      "env": {}
    },
    "news-search": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "tavily-mcp@0.2.19"],
      "env": {
        "TAVILY_API_KEY": "tvly-YOUR_KEY_HERE"
      }
    },
    "stockbit": {
      "command": "node",
      "args": ["/YOUR_PROJECT_PATH/stockbit-mcp/index.js"],
      "env": {}
    }
  }
}
```

Replace `YOUR_USER` and paths with actual values on the new machine.

---

## Step 9 — TradingView Setup (manual, one-time)

These must be configured manually inside TradingView Desktop:

**Screener 1 — "IDX Accumulation"** (Stock Screener → save as this name)

| Filter | Value |
|--------|-------|
| Exchange | Indonesia (IDX) |
| Type | Stock |
| Price | > 100 |
| Avg Volume (30d) | > 10,000,000 |
| Relative Volume | < 0.6 |
| RSI (14) | between 38 and 52 |

Sort: Relative Volume ascending. Columns: Close, Change%, Volume, Rel Vol, RSI(14).

**Screener 2 — "IDX Momentum"** (Stock Screener → save as this name, or rename to your preference)

| Filter | Value |
|--------|-------|
| Exchange | Indonesia (IDX) |
| Type | Stock |
| Price | > 100 |
| EMA (89) | less than Close |
| RSI (21) | greater than 54 |
| Relative Volume | greater than 1.0 |
| Volume × Price | greater than 5,000,000,000 |

Sort: Relative Volume descending.

**Pine Script Indicators** (Pine Editor → paste code → Save → Add to chart):

| File | Save as | Chart position |
|------|---------|---------------|
| `wyckoff_ichimoku_idx_analyzer.pine` | `Wyckoff_ichimoku analyzer 1` | Main price chart (overlay=true) |
| `volume_distribution_analyzer.pine` | `Volume Distribution Analysis` | Separate bottom panel (overlay=false) |

Both must be **visible on the chart** for `data_get_pine_tables` to read their dashboards.

---

## Step 10 — Project Hook (auto-start token server)

A Claude Code hook checks that the token server is running on every prompt. Located at:
`TV-Stock-Analysis/.claude/settings.json`

If the project is moved, update the absolute path inside the hook command.

---

## File Reference

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Claude's instructions — fill in your trading profile, workflow triggers, MCP quirks |
| `SETUP.md` | This file — full setup guide for new machine |
| `screener_workflow_guide.md` | Daily workflow, signal legend, entry rules |
| `trading_journal.md` | **Create your own** — SC Watch table + trade log (not included in repo, personal data) |
| `wyckoff_ichimoku_idx_analyzer.pine` | Main chart indicator source |
| `volume_distribution_analyzer.pine` | VDA bottom panel indicator source |
| `stockbit-mcp/index.js` | Stockbit MCP server (3 tools) |
| `stockbit-mcp/token-server.js` | Token receiver from Chrome extension |
| `stockbit-mcp/config.json` | Bearer token — **create from config.example.json, never commit** |
| `stockbit-mcp/config.example.json` | Template for config.json |
| `stockbit-mcp/extension/` | Chrome extension source |
| `~/Library/LaunchAgents/com.USERNAME.stockbit-token-server.plist` | macOS auto-start — create manually (see Step 4) |

---

## Trigger Phrases

| Say this | Claude does |
|----------|------------|
| `morning market check` | Full Priority 1 + 2 scan: Screener 2 → chart check → broker flow → news → Screener 1 spot-check |
| `evening analysis` | Sealed candle review: LPS flagging → SC Watch updates → Screener 1 thorough check → next-day prep |

---

## VPS / Portability Notes

**What can move to a VPS:**
- Stockbit MCP server (`index.js`, `token-server.js`) — no GUI needed
- News MCP (Tavily) — just npx
- Claude Code itself (if running as an agent)

**What cannot move to a VPS (requires screen):**
- TradingView Desktop — needs a display
- Chrome extension — needs Chrome browser
- TradingView MCP — connects to Desktop via CDP

**Option A — Hybrid (recommended):**
- VPS runs: Stockbit MCP + News MCP + Claude Code agent
- Local Mac runs: TradingView Desktop + TradingView MCP + Chrome (token refresh)
- Claude on VPS connects to TradingView MCP exposed via SSH tunnel or local network

**Option B — Full VPS (advanced):**
- VPS runs headless Chrome with TradingView web (not desktop)
- TradingView MCP connects to headless Chrome via CDP
- Requires: Xvfb (virtual display) or Chrome headless mode
- Token refresh: cron job that re-reads token from a shared secret store

**Docker approach (for Stockbit MCP only):**
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY stockbit-mcp/package*.json ./
RUN npm install
COPY stockbit-mcp/index.js stockbit-mcp/token-server.js ./
EXPOSE 3002
CMD ["node", "token-server.js"]
```
The MCP server itself is stdio-based (not HTTP) so it doesn't need a port — only the token server does.

**Next step recommendation:** SSH tunnel approach is the least disruptive. Run the full system on Mac, expose TradingView MCP port to VPS via reverse SSH tunnel. The VPS Claude agent connects back through the tunnel. No changes to existing setup required.

---

## Quick Verification Checklist (new machine)

Run these to confirm everything works before a scan:

```bash
# 1. TradingView Desktop running?
#    (manually check — app must be open)

# 2. TradingView MCP working?
#    → In Claude Code: tv_health_check should return cdp_connected: true

# 3. Token server running?
curl -s http://localhost:3002/health   # → {"ok":true}

# 4. Stockbit token valid?
#    → Run stockbit_broker_distribution("BBCA") in Claude — should return data, not 401

# 5. News MCP working?
#    → Claude spawns a Haiku news agent — should complete without error

# 6. Screeners saved in TradingView?
#    → Screener panel should show "IDX Accumulation" and "Erick Volum + Trend" in dropdown

# 7. Both Pine indicators on chart?
#    → data_get_pine_tables("Wyckoff") should return dashboard rows
#    → data_get_pine_tables("Volume Distribution") should return VDA rows
```

All 7 green = system ready.
