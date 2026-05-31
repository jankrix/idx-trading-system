#!/usr/bin/env node
/**
 * Stockbit Running Trade MCP Server
 * Fetches IDX running trade data from Stockbit API for Wyckoff delta analysis.
 *
 * Token setup: update config.json with your Bearer token.
 * Token expires daily — get a fresh one from Stockbit DevTools when you see 401.
 */

const { Server } = require("@modelcontextprotocol/sdk/server/index.js");
const { StdioServerTransport } = require("@modelcontextprotocol/sdk/server/stdio.js");
const { CallToolRequestSchema, ListToolsRequestSchema } = require("@modelcontextprotocol/sdk/types.js");
const https = require("https");
const fs = require("fs");
const path = require("path");

// ─── CONFIG ──────────────────────────────────────────────────────────────────

const CONFIG_PATH = path.join(__dirname, "config.json");
const BASE_HOST = "exodus.stockbit.com";
const LARGE_LOT = 100;

// Polite delay between API calls — keeps traffic indistinguishable from normal browsing
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const jitter = () => 400 + Math.floor(Math.random() * 300); // 400–700ms

function loadToken() {
  const cfg = JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
  return cfg.bearer_token;
}

// ─── HTTP HELPER ─────────────────────────────────────────────────────────────

function httpsGet(url) {
  return new Promise((resolve, reject) => {
    const token = loadToken();
    const req = https.get(url, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/json",
        "User-Agent": "Mozilla/5.0",
      },
    }, (res) => {
      if (res.statusCode === 401) {
        reject(new Error("401_UNAUTHORIZED"));
        return;
      }
      let data = "";
      res.on("data", chunk => data += chunk);
      res.on("end", () => {
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(new Error("Failed to parse JSON: " + data.slice(0, 200))); }
      });
    });
    req.on("error", reject);
  });
}

// ─── API ─────────────────────────────────────────────────────────────────────

async function fetchBrokerDistribution(symbol, tradeDate, period = "TB_PERIOD_LAST_1_DAY") {
  const params = new URLSearchParams({
    date: tradeDate || "",
    symbol: symbol.toUpperCase(),
    investor_type: "INVESTOR_TYPE_ALL",
    market_board: "MARKET_TYPE_REGULER",
    data_type: "BROKER_DISTRIBUTION_DATA_TYPE_VALUE",
    period,
  });
  const url = `https://${BASE_HOST}/order-trade/broker/distribution?${params}`;
  return httpsGet(url);
}

async function fetchRunningTrade(symbol, tradeDate, sort = "DESC", limit = 100) {
  const params = new URLSearchParams({
    "symbols[]": symbol.toUpperCase(),
    sort,
    limit: Math.min(limit, 100),
    order_by: "RUNNING_TRADE_ORDER_BY_TIME",
  });
  if (tradeDate) params.append("date", tradeDate);

  const url = `https://${BASE_HOST}/order-trade/running-trade?${params}`;
  const data = await httpsGet(url);
  const trades = data?.data?.running_trade ?? [];
  return trades.filter(t => t.market_board === "RG");
}

async function fetchOpenAndClose(symbol, tradeDate) {
  const open = await fetchRunningTrade(symbol, tradeDate, "ASC", 100);
  await sleep(jitter()); // polite pause between the two calls
  const close = await fetchRunningTrade(symbol, tradeDate, "DESC", 100);
  return { open, close };
}

// ─── ANALYSIS ────────────────────────────────────────────────────────────────

function parseLot(str) {
  return parseFloat(str.replace(/,/g, ""));
}

function brokerTypeShort(bt) {
  if (bt === "BROKER_TYPE_FOREIGN") return "F";
  if (bt === "BROKER_TYPE_GOVERNMENT") return "G";
  return "D";
}

function computeMetrics(trades) {
  let buyLots = 0, sellLots = 0, buyVal = 0, sellVal = 0;
  let fBuy = 0, fSell = 0, largeBuy = 0, largeSell = 0;
  const brokerNet = {};

  for (const t of trades) {
    const lots = parseLot(t.lot);
    const val  = t.value?.raw ?? 0;
    const isBuy = t.action === "buy";
    const buyerType  = brokerTypeShort(t.buyer_type  ?? "");
    const sellerType = brokerTypeShort(t.seller_type ?? "");
    const buyer  = t.buyer  ?? "?";
    const seller = t.seller ?? "?";

    if (isBuy) {
      buyLots += lots; buyVal += val;
      if (buyerType === "F") fBuy += lots;
      if (lots >= LARGE_LOT) largeBuy += lots;
      brokerNet[buyer] = (brokerNet[buyer] ?? 0) + lots;
    } else {
      sellLots += lots; sellVal += val;
      if (sellerType === "F") fSell += lots;
      if (lots >= LARGE_LOT) largeSell += lots;
      brokerNet[seller] = (brokerNet[seller] ?? 0) - lots;
    }
  }

  const total = buyLots + sellLots;
  const delta = buyLots - sellLots;
  const deltaPct = total > 0 ? (delta / total * 100) : 0;

  const sorted = Object.entries(brokerNet).sort((a, b) => b[1] - a[1]);
  const topBuyers  = sorted.filter(([,v]) => v > 0).slice(0, 3).map(([b, v]) => ({ broker: b, net_lots: Math.round(v) }));
  const topSellers = sorted.filter(([,v]) => v < 0).slice(0, 3).map(([b, v]) => ({ broker: b, net_lots: Math.round(Math.abs(v)) }));

  return {
    total_lots: Math.round(total),
    buy_lots:   Math.round(buyLots),
    sell_lots:  Math.round(sellLots),
    delta:      Math.round(delta),
    delta_pct:  Math.round(deltaPct * 10) / 10,
    foreign_buy:   Math.round(fBuy),
    foreign_sell:  Math.round(fSell),
    foreign_delta: Math.round(fBuy - fSell),
    large_lot_buy:  Math.round(largeBuy),
    large_lot_sell: Math.round(largeSell),
    top_buyers:  topBuyers,
    top_sellers: topSellers,
  };
}

function computeDeltaSummary(openClose, symbol, tradeDate) {
  const { open, close } = openClose;
  const o = computeMetrics(open);
  const c = computeMetrics(close);
  const combined = computeMetrics([...open, ...close]);

  let verdict;
  if (c.delta_pct > 20 && c.foreign_delta > 0)       verdict = "STRONG ACCUMULATION — foreign buying + close delta positive";
  else if (c.delta_pct > 10)                          verdict = "ACCUMULATION — net buying at close";
  else if (c.delta_pct < -20 && c.foreign_delta < 0) verdict = "STRONG DISTRIBUTION — foreign selling + close delta negative";
  else if (c.delta_pct < -10)                         verdict = "DISTRIBUTION — net selling at close";
  else if (Math.abs(c.delta_pct) <= 10 && c.large_lot_buy > c.large_lot_sell)
                                                       verdict = "ABSORPTION — balanced delta but large lots buying";
  else                                                 verdict = "NEUTRAL — no clear directional flow at close";

  return {
    symbol: symbol.toUpperCase(),
    date: tradeDate,
    verdict,
    open_session: {
      time_range: `${open.at(-1)?.time ?? "?"} — ${open[0]?.time ?? "?"}`,
      trades_sampled: open.length,
      ...o,
    },
    close_session: {
      time_range: `${close.at(-1)?.time ?? "?"} — ${close[0]?.time ?? "?"}`,
      trades_sampled: close.length,
      ...c,
    },
    combined_200: combined,
  };
}

function computeBrokerDistributionSummary(data, symbol, period) {
  const byValue = data?.data?.by_value ?? {};
  const buyers  = byValue.top_broker_buy  ?? [];
  const sellers = byValue.top_broker_sell ?? [];
  const date    = data?.data?.date_info   ?? data?.data?.start_date ?? "?";

  // Build net map: broker → { buy, sell, type }
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
    broker: code,
    type: v.type,                           // Asing/Lokal/Pemerintah
    buy_idr:  v.buy,
    sell_idr: v.sell,
    net_idr:  v.buy - v.sell,
  })).sort((a, b) => b.net_idr - a.net_idr);

  // Foreign net flow
  const foreignNet = brokerList
    .filter(b => b.type === "Asing")
    .reduce((s, b) => s + b.net_idr, 0);
  const localNet = brokerList
    .filter(b => b.type === "Lokal")
    .reduce((s, b) => s + b.net_idr, 0);

  const topAccumulators  = brokerList.filter(b => b.net_idr > 0).slice(0, 5);
  const topDistributors  = brokerList.filter(b => b.net_idr < 0).slice(-5).reverse();
  const dominant = brokerList[0];

  // Wyckoff verdict
  let verdict;
  if (foreignNet > 1e9)        verdict = "STRONG ACCUMULATION — foreign net buyers (>1B IDR)";
  else if (foreignNet > 0)     verdict = "ACCUMULATION — foreign net buyers";
  else if (foreignNet < -1e9)  verdict = "STRONG DISTRIBUTION — foreign net sellers (>1B IDR)";
  else if (foreignNet < 0)     verdict = "DISTRIBUTION — foreign net sellers";
  else if (localNet > 0)       verdict = "LOCAL ACCUMULATION — domestic net buyers, foreign neutral";
  else                         verdict = "NEUTRAL — no clear directional foreign flow";

  const fmt = (n) => {
    const abs = Math.abs(n);
    if (abs >= 1e9) return (n / 1e9).toFixed(2) + "B";
    if (abs >= 1e6) return (n / 1e6).toFixed(1) + "M";
    return n.toLocaleString();
  };

  return {
    symbol: symbol.toUpperCase(),
    date,
    period,
    verdict,
    foreign_net_idr: fmt(foreignNet),
    local_net_idr:   fmt(localNet),
    dominant_broker: dominant ? { broker: dominant.broker, type: dominant.type, net: fmt(dominant.net_idr) } : null,
    top_accumulators: topAccumulators.map(b => ({ broker: b.broker, type: b.type, net: fmt(b.net_idr) })),
    top_distributors: topDistributors.map(b => ({ broker: b.broker, type: b.type, net: fmt(b.net_idr) })),
  };
}

function computeBrokerFlow(trades, topN = 10) {
  const brokers = {};
  for (const t of trades) {
    const lots = parseLot(t.lot);
    const isBuy = t.action === "buy";
    const code  = isBuy ? t.buyer  : t.seller;
    const btype = brokerTypeShort(isBuy ? (t.buyer_type ?? "") : (t.seller_type ?? ""));
    if (!brokers[code]) brokers[code] = { broker: code, type: btype, buy: 0, sell: 0 };
    if (isBuy) brokers[code].buy  += lots;
    else       brokers[code].sell += lots;
  }

  return Object.values(brokers)
    .map(b => ({
      broker: b.broker,
      type: b.type,
      buy_lots:  Math.round(b.buy),
      sell_lots: Math.round(b.sell),
      net_lots:  Math.round(b.buy - b.sell),
      stance: (b.buy - b.sell) > 20 ? "ACCUMULATING" : (b.buy - b.sell) < -20 ? "DISTRIBUTING" : "NEUTRAL",
    }))
    .sort((a, b) => b.net_lots - a.net_lots)
    .slice(0, topN);
}

// ─── MCP SERVER ──────────────────────────────────────────────────────────────

const server = new Server(
  { name: "stockbit-running-trade", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "stockbit_delta_summary",
      description: "Wyckoff delta analysis for an IDX stock. Returns open/close session buy-sell split, foreign flow, large lot activity, top brokers, and a verdict (ACCUMULATION/DISTRIBUTION/NEUTRAL). Uses first 100 (open) + last 100 (close) trades of the day.",
      inputSchema: {
        type: "object",
        properties: {
          symbol: { type: "string", description: "IDX stock symbol e.g. GGRM, BBCA" },
          date:   { type: "string", description: "YYYY-MM-DD. Defaults to today." },
        },
        required: ["symbol"],
      },
    },
    {
      name: "stockbit_broker_distribution",
      description: "Full-day broker accumulation/distribution for an IDX stock. Uses the Stockbit broker distribution endpoint — complete day data (not sampled). Shows foreign vs local net flow, dominant broker (Bandar), top accumulators and distributors. More accurate than stockbit_broker_flow for Wyckoff analysis.",
      inputSchema: {
        type: "object",
        properties: {
          symbol: { type: "string", description: "IDX stock symbol e.g. GGRM" },
          date:   { type: "string", description: "YYYY-MM-DD. Leave empty for latest session." },
          period: {
            type: "string",
            description: "TB_PERIOD_LAST_1_DAY (default), TB_PERIOD_LAST_5_DAY, TB_PERIOD_LAST_30_DAY",
            default: "TB_PERIOD_LAST_1_DAY",
          },
        },
        required: ["symbol"],
      },
    },
    {
      name: "stockbit_broker_flow",
      description: "Per-broker net positions derived from running trade samples (open + close 200 records). Use stockbit_broker_distribution instead for full-day accuracy.",
      inputSchema: {
        type: "object",
        properties: {
          symbol: { type: "string" },
          date:   { type: "string", description: "YYYY-MM-DD, defaults to today" },
          top_n:  { type: "number", description: "Return top N brokers. Default 10.", default: 10 },
        },
        required: ["symbol"],
      },
    },
    {
      name: "stockbit_running_trade",
      description: "Raw running trade records for an IDX stock. Use stockbit_delta_summary for Wyckoff analysis; this is for deep inspection.",
      inputSchema: {
        type: "object",
        properties: {
          symbol: { type: "string" },
          date:   { type: "string", description: "YYYY-MM-DD, defaults to today" },
          sort:   { type: "string", enum: ["DESC", "ASC"], description: "DESC=latest first (close), ASC=earliest first (open). Default DESC." },
        },
        required: ["symbol"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  const symbol = (args.symbol ?? "").toUpperCase();
  const tradeDate = args.date ?? new Date().toISOString().split("T")[0];

  try {
    await sleep(jitter()); // space out consecutive symbol requests
    if (name === "stockbit_delta_summary") {
      const oc = await fetchOpenAndClose(symbol, tradeDate);
      if (!oc.open.length && !oc.close.length) {
        return { content: [{ type: "text", text: `No running trade data for ${symbol} on ${tradeDate}. Market may be closed or holiday.` }] };
      }
      const summary = computeDeltaSummary(oc, symbol, tradeDate);
      return { content: [{ type: "text", text: JSON.stringify(summary, null, 2) }] };
    }

    if (name === "stockbit_broker_distribution") {
      const period = args.period ?? "TB_PERIOD_LAST_1_DAY";
      const raw = await fetchBrokerDistribution(symbol, tradeDate, period);
      if (!raw?.data?.by_value?.top_broker_buy?.length) {
        return { content: [{ type: "text", text: `No broker distribution data for ${symbol} on ${tradeDate}.` }] };
      }
      const summary = computeBrokerDistributionSummary(raw, symbol, period);
      return { content: [{ type: "text", text: JSON.stringify(summary, null, 2) }] };
    }

    if (name === "stockbit_broker_flow") {
      const topN = args.top_n ?? 10;
      const oc = await fetchOpenAndClose(symbol, tradeDate);
      const all = [...oc.open, ...oc.close];
      if (!all.length) return { content: [{ type: "text", text: `No data for ${symbol} on ${tradeDate}.` }] };
      const flow = computeBrokerFlow(all, topN);
      return { content: [{ type: "text", text: JSON.stringify(flow, null, 2) }] };
    }

    if (name === "stockbit_running_trade") {
      const sort = args.sort ?? "DESC";
      const trades = await fetchRunningTrade(symbol, tradeDate, sort, 100);
      return { content: [{ type: "text", text: JSON.stringify(trades, null, 2) }] };
    }

    return { content: [{ type: "text", text: `Unknown tool: ${name}` }] };

  } catch (err) {
    if (err.message === "401_UNAUTHORIZED") {
      return { content: [{ type: "text", text: "401 Unauthorized — Bearer token expired. Update bearer_token in stockbit-mcp/config.json with a fresh token from Stockbit DevTools (Network tab → any request → Authorization header)." }] };
    }
    return { content: [{ type: "text", text: `Error: ${err.message}` }] };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch(console.error);
