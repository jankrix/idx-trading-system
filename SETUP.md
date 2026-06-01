# IDX Swing Trading System — Setup Guide

This file is the single source of truth for replicating the full trading system on a new machine.
Read this first before touching any other file.

---

## System Overview

All components feed into Claude Code, which runs the analysis:

```
TradingView Desktop ──CDP──► TradingView MCP ──────────────────────────┐
                                                                        │
Stockbit Web ──token──► Chrome Extension                                │
                              │                                         ▼
                         Token Server ──config.json──► Stockbit MCP ──► Claude Code
                                                                        ▲
finnhub-mcp/config.json ──────────────────────────► Finnhub MCP ───────┤
                                                                        │
Tavily API key (in ~/.claude.json) ──────────────► News MCP (Tavily) ──┘
```

| Component | What it does | Market | Required? |
|-----------|-------------|--------|-----------|
| **Claude Code** | The AI agent that runs all analysis | Both | Yes |
| **TradingView Desktop** | Charting app — Claude controls it via CDP | Both | Yes |
| **TradingView MCP** | Bridge between Claude and TradingView Desktop | Both | Yes |
| **Stockbit MCP** | Full-day broker flow (foreign vs local net flow) | IDX only | Yes |
| **Token Server** | Receives Stockbit token from Chrome extension | IDX only | Yes |
| **Chrome Extension** | Auto-captures Stockbit Bearer token daily | IDX only | Recommended |
| **Finnhub MCP** | Earnings calendar + analyst consensus for US stocks | US only | Yes |
| **News MCP (Tavily)** | Deep qualitative news search | Both | Yes |

---

## Analysis Architecture — 3-Tier System

Different tiers are used for IDX vs US stocks:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    IDX STOCK ANALYSIS                               │
├──────────────────────┬──────────────────────┬───────────────────────┤
│   TIER 1: CHART      │  TIER 2: FLOW        │  TIER 3: NEWS        │
│   TradingView MCP    │  Stockbit MCP        │  Tavily MCP          │
│   ────────────────   │  ────────────────    │  ────────────────    │
│   Wyckoff signals    │  Foreign net (IDR)   │  Earnings/news       │
│   Ichimoku locks     │  Dominant broker     │  Sector context      │
│   VDA volume         │  Absorption/dist.    │  Macro catalysts     │
│   "Is the pattern    │  "WHO is behind      │  "WHY is this        │
│    valid?"           │   the move?"         │   moving?"           │
├──────────────────────┴──────────────────────┴───────────────────────┤
│  Decision: Chart signal + Flow confirm + No negative news = ENTER   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    US STOCK ANALYSIS                                │
├──────────────────────┬──────────────────────┬───────────────────────┤
│   TIER 1: CHART      │  TIER 2: FUNDAMENTAL │  TIER 3: NEWS        │
│   TradingView MCP    │  Finnhub MCP         │  Tavily MCP          │
│   ────────────────   │  ────────────────    │  ────────────────    │
│   Price action       │  Analyst consensus   │  Earnings narrative  │
│   Trend direction    │  Earnings calendar   │  Sector tailwinds    │
│   Support/resist     │  Buy/hold/sell count │  Competitive news    │
│   "Where is price    │  "What do analysts   │  "What's the story   │
│    technically?"     │   say numerically?"  │   behind the move?"  │
├──────────────────────┴──────────────────────┴───────────────────────┤
│  Decision: Chart trend + Analyst consensus + Catalyst = HOLD/ENTER  │
└─────────────────────────────────────────────────────────────────────┘
```

**Key principle:** Tiers are hierarchical, not voting. Chart (Tier 1) is always primary — price is truth. Tier 2 confirms conviction. Tier 3 explains context. They don't vote against each other; they add layers of confidence.

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

The project lives in two folders:

```
~/Documents/Erick-claude-workspace/brainstorm-digi-product/
├── TV-Stock-Analysis/        ← Pine scripts, journals, workflow guides (this folder)
└── stockbit-mcp/             ← Stockbit MCP server + Chrome extension
```

Also needed separately:
```
~/tradingview-mcp/            ← TradingView MCP server (separate repo)
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
cd ~/Documents/Erick-claude-workspace/brainstorm-digi-product/stockbit-mcp
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
cd ~/Documents/Erick-claude-workspace/brainstorm-digi-product/stockbit-mcp
node token-server.js
# Should print: Stockbit Token Server running on localhost:3002
```

**Install as a macOS launchd service (auto-starts on login, auto-restarts on crash):**
```bash
# Copy the plist (already created, just load it)
launchctl load ~/Library/LaunchAgents/com.erick.stockbit-token-server.plist

# Verify running
curl -s http://localhost:3002/health   # → {"ok":true}

# View logs
tail -f ~/Library/Logs/stockbit-token-server.log
```

**Manage the service:**
```bash
launchctl unload ~/Library/LaunchAgents/com.erick.stockbit-token-server.plist  # Stop
launchctl load   ~/Library/LaunchAgents/com.erick.stockbit-token-server.plist  # Start
```

**The plist file** (`~/Library/LaunchAgents/com.erick.stockbit-token-server.plist`) points to:
- Node: `/opt/homebrew/bin/node`
- Script: full path to `token-server.js`

If node is at a different path on the new machine, update the plist `<string>` for the node binary.

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

## Step 7 — Finnhub MCP (US stocks only)

Provides earnings calendar + analyst consensus for US portfolio analysis. Free tier, permanent API key (no daily refresh).

```bash
cd finnhub-mcp
npm install
cp config.example.json config.json
# Edit config.json and paste your API key
```

**Get a free API key:** https://finnhub.io/register (no credit card, permanent key)

**Test it works:**
```bash
node -e "
const https = require('https');
const key = require('./config.json').api_key;
https.get('https://finnhub.io/api/v1/quote?symbol=AAPL&token=' + key, r => {
  let d=''; r.on('data',c=>d+=c);
  r.on('end',()=>console.log('AAPL:', JSON.parse(d).c, '— OK'));
});
"
```

**5 tools available:**

| Tool | What it returns |
|------|----------------|
| `finnhub_us_portfolio_check` | **All holdings at once** — price + analyst consensus + next earnings date |
| `finnhub_earnings` | Next earnings date, EPS estimate for any US stock |
| `finnhub_recommendation` | Analyst buy/hold/sell counts + consensus verdict |
| `finnhub_quote` | Current price, change%, high/low |
| `finnhub_news` | Last N days of headlines |

**Usage:** call `finnhub_us_portfolio_check(["AAPL","NVDA","MSFT"...])` at the start of any US portfolio review — one call covers all 11 stocks.

---

## Step 8 — News MCP (Tavily)

Used by Claude to search news for each ticker during morning/evening scans.

**No installation needed** — it uses `npx` and downloads automatically.

**Requires a Tavily API key.** Get one free at https://tavily.com

The API key is stored in `~/.claude.json` under `mcpServers.news-search.env.TAVILY_API_KEY`.

---

## Step 9 — Register All MCPs in Claude Code

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
    },
    "finnhub": {
      "command": "node",
      "args": ["/YOUR_PROJECT_PATH/finnhub-mcp/index.js"],
      "env": {}
    }
  }
}
```

Replace `YOUR_PROJECT_PATH` with the actual path on the new machine.

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

**Screener 2 — "Erick Volum + Trend"** (Stock Screener → save as this name)

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
| `TV-Stock-Analysis/CLAUDE.md` | Claude's instructions — trading profile, workflow triggers, MCP quirks |
| `TV-Stock-Analysis/SETUP.md` | This file — full setup guide for new machine |
| `TV-Stock-Analysis/screener_workflow_guide.md` | Daily workflow, signal legend, entry rules |
| `TV-Stock-Analysis/trading_journal.md` | SC Watch + trading account journal |
| `TV-Stock-Analysis/investment_portfolio_journal.md` | Long-term IDX portfolio journal |
| `TV-Stock-Analysis/us_portfolio_journal.md` | US stocks portfolio journal |
| `TV-Stock-Analysis/wyckoff_ichimoku_idx_analyzer.pine` | Main chart indicator source |
| `TV-Stock-Analysis/volume_distribution_analyzer.pine` | VDA bottom panel indicator source |
| `stockbit-mcp/index.js` | Stockbit MCP — 3 tools (IDX broker flow) |
| `stockbit-mcp/token-server.js` | Token receiver from Chrome extension |
| `stockbit-mcp/config.json` | Stockbit Bearer token — **never commit** |
| `stockbit-mcp/extension/` | Chrome extension source |
| `finnhub-mcp/index.js` | Finnhub MCP — 5 tools (US earnings + analyst consensus) |
| `finnhub-mcp/config.json` | Finnhub API key — **never commit** |
| `~/Library/LaunchAgents/com.USERNAME.stockbit-token-server.plist` | macOS auto-start config |

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
