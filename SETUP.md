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

Clone this repo, then create `stockbit-mcp/` as a sibling folder:

```
<your-project-path>/
├── idx-trading-system/   ← this repo (Pine scripts, journals, CLAUDE.md, SETUP.md)
│   └── stockbit-mcp/     ← Stockbit MCP lives inside the repo
└── tradingview-mcp/      ← TradingView MCP (separate repo, see Step 2)
```

> `stockbit-mcp/` is already included inside this repo — no separate clone needed.

Update all absolute paths in `~/.claude.json` and the launchd plist to match where you cloned the repo.

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

The Stockbit MCP is a custom Node.js server that connects to Stockbit's private API using your Bearer token. The source is included in the `stockbit-mcp/` folder of this repo. If you're setting up from scratch, create each file below.

### 3a — Folder structure

```
stockbit-mcp/
├── index.js            ← MCP server (4 tools)
├── token-server.js     ← HTTP server that receives token from Chrome extension
├── package.json        ← dependencies
├── config.json         ← Bearer token (never commit — listed in .gitignore)
├── config.example.json ← empty template to commit
└── extension/          ← Chrome extension (4 files)
    ├── manifest.json
    ├── background.js
    ├── popup.html
    └── popup.js
```

### 3b — package.json

```json
{
  "name": "stockbit-mcp",
  "version": "1.0.0",
  "main": "index.js",
  "type": "commonjs",
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.29.0",
    "node-fetch": "^3.3.2"
  }
}
```

### 3c — config.json (create manually, never commit)

```json
{ "bearer_token": "" }
```

Also create `config.example.json` with the same empty template — this one is safe to commit.

Add to `.gitignore`:
```
stockbit-mcp/config.json
stockbit-mcp/node_modules/
```

### 3d — index.js (MCP server)

This file registers 4 MCP tools and handles all Stockbit API calls. Full source:

```js
#!/usr/bin/env node

const { Server } = require("@modelcontextprotocol/sdk/server/index.js");
const { StdioServerTransport } = require("@modelcontextprotocol/sdk/server/stdio.js");
const { CallToolRequestSchema, ListToolsRequestSchema } = require("@modelcontextprotocol/sdk/types.js");
const https = require("https");
const fs = require("fs");
const path = require("path");

const CONFIG_PATH = path.join(__dirname, "config.json");
const BASE_HOST = "exodus.stockbit.com";
const LARGE_LOT = 100;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const jitter = () => 400 + Math.floor(Math.random() * 300);

function loadToken() {
  return JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8")).bearer_token;
}

function httpsGet(url) {
  return new Promise((resolve, reject) => {
    const token = loadToken();
    const req = https.get(url, {
      headers: { Authorization: `Bearer ${token}`, Accept: "application/json", "User-Agent": "Mozilla/5.0" },
    }, (res) => {
      if (res.statusCode === 401) { reject(new Error("401_UNAUTHORIZED")); return; }
      let data = "";
      res.on("data", chunk => data += chunk);
      res.on("end", () => { try { resolve(JSON.parse(data)); } catch (e) { reject(new Error("Failed to parse JSON")); } });
    });
    req.on("error", reject);
  });
}

async function fetchBrokerDistribution(symbol, tradeDate, period = "TB_PERIOD_LAST_1_DAY") {
  const params = new URLSearchParams({ date: tradeDate || "", symbol: symbol.toUpperCase(),
    investor_type: "INVESTOR_TYPE_ALL", market_board: "MARKET_TYPE_REGULER",
    data_type: "BROKER_DISTRIBUTION_DATA_TYPE_VALUE", period });
  return httpsGet(`https://${BASE_HOST}/order-trade/broker/distribution?${params}`);
}

async function fetchRunningTrade(symbol, tradeDate, sort = "DESC", limit = 100) {
  const params = new URLSearchParams({ "symbols[]": symbol.toUpperCase(), sort, limit: Math.min(limit, 100),
    order_by: "RUNNING_TRADE_ORDER_BY_TIME" });
  if (tradeDate) params.append("date", tradeDate);
  const data = await httpsGet(`https://${BASE_HOST}/order-trade/running-trade?${params}`);
  return (data?.data?.running_trade ?? []).filter(t => t.market_board === "RG");
}

async function fetchOpenAndClose(symbol, tradeDate) {
  const open = await fetchRunningTrade(symbol, tradeDate, "ASC", 100);
  await sleep(jitter());
  const close = await fetchRunningTrade(symbol, tradeDate, "DESC", 100);
  return { open, close };
}

function parseLot(str) { return parseFloat(str.replace(/,/g, "")); }
function brokerTypeShort(bt) {
  if (bt === "BROKER_TYPE_FOREIGN") return "F";
  if (bt === "BROKER_TYPE_GOVERNMENT") return "G";
  return "D";
}

function computeMetrics(trades) {
  let buyLots = 0, sellLots = 0;
  let fBuy = 0, fSell = 0, largeBuy = 0, largeSell = 0;
  const brokerNet = {};
  for (const t of trades) {
    const lots = parseLot(t.lot), isBuy = t.action === "buy";
    const buyerType = brokerTypeShort(t.buyer_type ?? ""), sellerType = brokerTypeShort(t.seller_type ?? "");
    const buyer = t.buyer ?? "?", seller = t.seller ?? "?";
    if (isBuy) {
      buyLots += lots;
      if (buyerType === "F") fBuy += lots;
      if (lots >= LARGE_LOT) largeBuy += lots;
      brokerNet[buyer] = (brokerNet[buyer] ?? 0) + lots;
    } else {
      sellLots += lots;
      if (sellerType === "F") fSell += lots;
      if (lots >= LARGE_LOT) largeSell += lots;
      brokerNet[seller] = (brokerNet[seller] ?? 0) - lots;
    }
  }
  const total = buyLots + sellLots, delta = buyLots - sellLots;
  const sorted = Object.entries(brokerNet).sort((a, b) => b[1] - a[1]);
  return {
    total_lots: Math.round(total), buy_lots: Math.round(buyLots), sell_lots: Math.round(sellLots),
    delta: Math.round(delta), delta_pct: Math.round(delta / (total || 1) * 1000) / 10,
    foreign_buy: Math.round(fBuy), foreign_sell: Math.round(fSell), foreign_delta: Math.round(fBuy - fSell),
    large_lot_buy: Math.round(largeBuy), large_lot_sell: Math.round(largeSell),
    top_buyers:  sorted.filter(([,v]) => v > 0).slice(0,3).map(([b,v]) => ({ broker: b, net_lots: Math.round(v) })),
    top_sellers: sorted.filter(([,v]) => v < 0).slice(0,3).map(([b,v]) => ({ broker: b, net_lots: Math.round(Math.abs(v)) })),
  };
}

function computeDeltaSummary(openClose, symbol, tradeDate) {
  const { open, close } = openClose;
  const o = computeMetrics(open), c = computeMetrics(close), combined = computeMetrics([...open, ...close]);
  let verdict;
  if (c.delta_pct > 20 && c.foreign_delta > 0)       verdict = "STRONG ACCUMULATION — foreign buying + close delta positive";
  else if (c.delta_pct > 10)                          verdict = "ACCUMULATION — net buying at close";
  else if (c.delta_pct < -20 && c.foreign_delta < 0)  verdict = "STRONG DISTRIBUTION — foreign selling + close delta negative";
  else if (c.delta_pct < -10)                         verdict = "DISTRIBUTION — net selling at close";
  else if (Math.abs(c.delta_pct) <= 10 && c.large_lot_buy > c.large_lot_sell)
                                                       verdict = "ABSORPTION — balanced delta but large lots buying";
  else                                                 verdict = "NEUTRAL — no clear directional flow at close";
  return { symbol: symbol.toUpperCase(), date: tradeDate, verdict,
    open_session:  { time_range: `${open.at(-1)?.time ?? "?"} — ${open[0]?.time ?? "?"}`,  trades_sampled: open.length,  ...o },
    close_session: { time_range: `${close.at(-1)?.time ?? "?"} — ${close[0]?.time ?? "?"}`, trades_sampled: close.length, ...c },
    combined_200: combined };
}

function computeBrokerDistributionSummary(data, symbol, period) {
  const byValue = data?.data?.by_value ?? {};
  const buyers = byValue.top_broker_buy ?? [], sellers = byValue.top_broker_sell ?? [];
  const date = data?.data?.date_info ?? data?.data?.start_date ?? "?";
  const net = {};
  for (const b of buyers) {
    const code = b.detail.code;
    if (!net[code]) net[code] = { buy: 0, sell: 0, type: b.detail.type };
    net[code].buy += b.detail.amount;
  }
  for (const s of sellers) {
    const code = s.detail.code;
    if (!net[code]) net[code] = { buy: 0, sell: 0, type: s.detail.type };
    net[code].sell += s.detail.amount;
  }
  const brokerList = Object.entries(net).map(([code, v]) => ({
    broker: code, type: v.type, net_idr: v.buy - v.sell,
  })).sort((a, b) => b.net_idr - a.net_idr);
  const foreignNet = brokerList.filter(b => b.type === "Asing").reduce((s,b) => s + b.net_idr, 0);
  const localNet   = brokerList.filter(b => b.type === "Lokal").reduce((s,b) => s + b.net_idr, 0);
  const fmt = (n) => {
    const abs = Math.abs(n);
    if (abs >= 1e9) return (n/1e9).toFixed(2)+"B";
    if (abs >= 1e6) return (n/1e6).toFixed(1)+"M";
    return n.toLocaleString();
  };
  let verdict;
  if (foreignNet > 1e9)       verdict = "STRONG ACCUMULATION — foreign net buyers (>1B IDR)";
  else if (foreignNet > 0)    verdict = "ACCUMULATION — foreign net buyers";
  else if (foreignNet < -1e9) verdict = "STRONG DISTRIBUTION — foreign net sellers (>1B IDR)";
  else if (foreignNet < 0)    verdict = "DISTRIBUTION — foreign net sellers";
  else if (localNet > 0)      verdict = "LOCAL ACCUMULATION — domestic net buyers, foreign neutral";
  else                        verdict = "NEUTRAL — no clear directional foreign flow";
  return { symbol: symbol.toUpperCase(), date, period, verdict,
    foreign_net_idr: fmt(foreignNet), local_net_idr: fmt(localNet),
    dominant_broker: brokerList[0] ? { broker: brokerList[0].broker, type: brokerList[0].type, net: fmt(brokerList[0].net_idr) } : null,
    top_accumulators: brokerList.filter(b => b.net_idr > 0).slice(0,5).map(b => ({ broker: b.broker, type: b.type, net: fmt(b.net_idr) })),
    top_distributors: brokerList.filter(b => b.net_idr < 0).slice(-5).reverse().map(b => ({ broker: b.broker, type: b.type, net: fmt(b.net_idr) })),
  };
}

function computeBrokerFlow(trades, topN = 10) {
  const brokers = {};
  for (const t of trades) {
    const lots = parseLot(t.lot), isBuy = t.action === "buy";
    const code = isBuy ? t.buyer : t.seller;
    const btype = brokerTypeShort(isBuy ? (t.buyer_type ?? "") : (t.seller_type ?? ""));
    if (!brokers[code]) brokers[code] = { broker: code, type: btype, buy: 0, sell: 0 };
    if (isBuy) brokers[code].buy += lots; else brokers[code].sell += lots;
  }
  return Object.values(brokers)
    .map(b => ({ broker: b.broker, type: b.type, buy_lots: Math.round(b.buy), sell_lots: Math.round(b.sell),
      net_lots: Math.round(b.buy - b.sell),
      stance: (b.buy - b.sell) > 20 ? "ACCUMULATING" : (b.buy - b.sell) < -20 ? "DISTRIBUTING" : "NEUTRAL" }))
    .sort((a, b) => b.net_lots - a.net_lots).slice(0, topN);
}

const server = new Server(
  { name: "stockbit-running-trade", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    { name: "stockbit_broker_distribution",
      description: "Full-day broker accumulation/distribution for an IDX stock. Shows foreign vs local net flow, dominant broker (Bandar), top accumulators and distributors.",
      inputSchema: { type: "object", properties: {
        symbol: { type: "string", description: "IDX stock symbol e.g. GGRM" },
        date:   { type: "string", description: "YYYY-MM-DD. Leave empty for latest session." },
        period: { type: "string", description: "TB_PERIOD_LAST_1_DAY (default), TB_PERIOD_LAST_5_DAY, TB_PERIOD_LAST_30_DAY", default: "TB_PERIOD_LAST_1_DAY" },
      }, required: ["symbol"] } },
    { name: "stockbit_delta_summary",
      description: "Wyckoff delta analysis — open/close session buy-sell split, foreign flow, large lot activity, verdict.",
      inputSchema: { type: "object", properties: {
        symbol: { type: "string" }, date: { type: "string", description: "YYYY-MM-DD. Defaults to today." },
      }, required: ["symbol"] } },
    { name: "stockbit_broker_flow",
      description: "Per-broker net positions from running trade samples. Use stockbit_broker_distribution for full-day accuracy.",
      inputSchema: { type: "object", properties: {
        symbol: { type: "string" }, date: { type: "string" }, top_n: { type: "number", default: 10 },
      }, required: ["symbol"] } },
    { name: "stockbit_running_trade",
      description: "Raw running trade records. Use stockbit_delta_summary for analysis; this is for deep inspection.",
      inputSchema: { type: "object", properties: {
        symbol: { type: "string" }, date: { type: "string" }, sort: { type: "string", enum: ["DESC","ASC"] },
      }, required: ["symbol"] } },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  const symbol = (args.symbol ?? "").toUpperCase();
  const tradeDate = args.date ?? new Date().toISOString().split("T")[0];
  try {
    await sleep(jitter());
    if (name === "stockbit_broker_distribution") {
      const period = args.period ?? "TB_PERIOD_LAST_1_DAY";
      const raw = await fetchBrokerDistribution(symbol, tradeDate, period);
      if (!raw?.data?.by_value?.top_broker_buy?.length)
        return { content: [{ type: "text", text: `No broker distribution data for ${symbol} on ${tradeDate}.` }] };
      return { content: [{ type: "text", text: JSON.stringify(computeBrokerDistributionSummary(raw, symbol, period), null, 2) }] };
    }
    if (name === "stockbit_delta_summary") {
      const oc = await fetchOpenAndClose(symbol, tradeDate);
      if (!oc.open.length && !oc.close.length)
        return { content: [{ type: "text", text: `No running trade data for ${symbol} on ${tradeDate}.` }] };
      return { content: [{ type: "text", text: JSON.stringify(computeDeltaSummary(oc, symbol, tradeDate), null, 2) }] };
    }
    if (name === "stockbit_broker_flow") {
      const oc = await fetchOpenAndClose(symbol, tradeDate);
      const all = [...oc.open, ...oc.close];
      if (!all.length) return { content: [{ type: "text", text: `No data for ${symbol} on ${tradeDate}.` }] };
      return { content: [{ type: "text", text: JSON.stringify(computeBrokerFlow(all, args.top_n ?? 10), null, 2) }] };
    }
    if (name === "stockbit_running_trade") {
      const trades = await fetchRunningTrade(symbol, tradeDate, args.sort ?? "DESC", 100);
      return { content: [{ type: "text", text: JSON.stringify(trades, null, 2) }] };
    }
    return { content: [{ type: "text", text: `Unknown tool: ${name}` }] };
  } catch (err) {
    if (err.message === "401_UNAUTHORIZED")
      return { content: [{ type: "text", text: "401 Unauthorized — Bearer token expired. Update bearer_token in config.json." }] };
    return { content: [{ type: "text", text: `Error: ${err.message}` }] };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}
main().catch(console.error);
```

### 3e — token-server.js

```js
#!/usr/bin/env node
const http = require("http");
const fs   = require("fs");
const path = require("path");

const PORT   = 3002;
const CONFIG = path.join(__dirname, "config.json");

const server = http.createServer((req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") { res.writeHead(204); res.end(); return; }
  if (req.method === "GET" && req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true })); return;
  }
  if (req.method === "POST" && req.url === "/token") {
    let body = "";
    req.on("data", c => body += c);
    req.on("end", () => {
      try {
        const { token } = JSON.parse(body);
        if (!token) throw new Error("Invalid token");
        const cfg = fs.existsSync(CONFIG) ? JSON.parse(fs.readFileSync(CONFIG, "utf8")) : {};
        cfg.bearer_token = token;
        fs.writeFileSync(CONFIG, JSON.stringify(cfg, null, 2));
        console.log(`[${new Date().toLocaleTimeString("id-ID")}] Token updated`);
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true }));
      } catch (err) {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: false, error: err.message }));
      }
    }); return;
  }
  res.writeHead(404); res.end();
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`Stockbit Token Server running on localhost:${PORT}`);
});
```

### 3f — Chrome extension files

**extension/manifest.json**
```json
{
  "manifest_version": 3,
  "name": "Stockbit Token Sync",
  "version": "1.0",
  "description": "Captures Stockbit Bearer token and syncs it to the local MCP server config.",
  "permissions": ["webRequest", "storage"],
  "host_permissions": ["https://*.stockbit.com/*", "http://localhost:3002/*"],
  "background": { "service_worker": "background.js" },
  "action": { "default_popup": "popup.html" }
}
```

**extension/background.js**
```js
// Intercept requests to exodus.stockbit.com and capture the Bearer token
chrome.webRequest.onBeforeSendHeaders.addListener(
  (details) => {
    const authHeader = details.requestHeaders?.find(h => h.name.toLowerCase() === "authorization");
    if (authHeader?.value?.startsWith("Bearer ")) {
      const token = authHeader.value.replace("Bearer ", "").trim();
      chrome.storage.local.set({ token, captured_at: new Date().toISOString(), synced: false });
    }
  },
  { urls: ["https://exodus.stockbit.com/*"] },
  ["requestHeaders"]
);
```

**extension/popup.html** — see source in `stockbit-mcp/extension/popup.html` (dark UI with sync button)

**extension/popup.js** — reads token from storage, POSTs to `localhost:3002/token` on button click

### 3g — Install and test

```bash
cd <repo-root>/stockbit-mcp
npm install

# Test token server
node token-server.js &
curl -s http://localhost:3002/health   # → {"ok":true}
kill %1
```

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
cd <repo-root>/stockbit-mcp
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
`.claude/settings.json` (in the repo root)

If the project is moved, update the absolute path inside the hook command.

---

## File Reference

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Claude's instructions — trading profile, workflow triggers, MCP quirks |
| `SETUP.md` | This file — full setup guide for new machine |
| `screener_workflow_guide.md` | Daily workflow, signal legend, entry rules |
| `trading_journal.md` | SC Watch + trading account journal |
| `investment_portfolio_journal.md` | Long-term IDX portfolio journal |
| `us_portfolio_journal.md` | US stocks portfolio journal |
| `wyckoff_ichimoku_idx_analyzer.pine` | Main chart indicator source |
| `wyckoff_ichimoku_break21_analyzer.pine` | Combined Wyckoff + Ichimoku + Break 21 indicator source |
| `volume_distribution_analyzer.pine` | VDA bottom panel indicator source |
| `bandar_dashboard.py` | Bandar Intelligence Dashboard — batch screener → HTML output |
| `scalp_server.py` | Scalp Monitor — live tape reader at http://localhost:8765/ |
| `stockbit-mcp/index.js` | Stockbit MCP — 8 tools (IDX screeners + broker flow + fundamentals) |
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

```bash
# 8. Scalp Monitor working? (optional — only needed for intraday tape reading)
python3 scalp_server.py &
curl -s http://localhost:8765/ | grep -c "Scalp Monitor"   # → 1
kill %1
```
