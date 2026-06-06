#!/usr/bin/env python3
"""
Scalp Monitor — live tape reader for IDX stocks.
Polls Stockbit running trade every 3s and applies rule-based signals.

Run:   python3 scalp_server.py
Open:  http://localhost:8765/
Token: same stockbit-mcp/config.json used by bandar_dashboard.py
"""

import json, time, threading, sys
import urllib.request, urllib.parse, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import deque
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────────

PORT          = 8765
POLL_INTERVAL = 3      # seconds between Stockbit polls
BUFFER_SIZE   = 300    # max trades to keep in memory per symbol
LARGE_LOT     = 500    # lots — highlight
BANDAR_LOT    = 2000   # lots — strong alert
BUY_PRESS_N   = 20     # rolling window for buy pressure
ABS_WINDOW    = 5      # trades for absorption check
MOM_WINDOW    = 6      # consecutive prices for momentum

SCRIPT_DIR  = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR.parent / "stockbit-mcp/config.json"
BASE_HOST   = "exodus.stockbit.com"

# ─── SHARED STATE (thread-safe via lock) ──────────────────────────────────────

_state_lock = threading.Lock()
_state = {}  # symbol -> {trades, signals, stats, last_update, error}
_pollers = {}  # symbol -> ScalpPoller thread

# ─── HTTP ─────────────────────────────────────────────────────────────────────

def load_token():
    return json.loads(CONFIG_PATH.read_text())["bearer_token"]

def api_get(path, params=None):
    token = load_token()
    url = f"https://{BASE_HOST}{path}"
    if params:
        url += "?" + urllib.parse.urlencode([(k, v) for k, v in params.items() if v is not None])
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

# ─── TRADE UTILS ─────────────────────────────────────────────────────────────

def parse_lot(s):
    try:
        return float(str(s).replace(",", ""))
    except:
        return 0.0

def derive_price(trade):
    """Derive price from value/lot since there's no direct price field."""
    lots = parse_lot(trade.get("lot", 0))
    raw_val = trade.get("value", {})
    val = raw_val.get("raw", 0) if isinstance(raw_val, dict) else float(raw_val or 0)
    if lots > 0 and val > 0:
        return val / (lots * 100)
    return 0.0

def broker_type_short(bt):
    if bt == "BROKER_TYPE_FOREIGN":   return "F"
    if bt == "BROKER_TYPE_GOVERNMENT": return "G"
    return "D"

def trade_key(t):
    """Deduplication key: time + action + lot + broker."""
    action = t.get("action", "")
    broker = t.get("buyer", "") if action == "buy" else t.get("seller", "")
    return (t.get("time", ""), action, t.get("lot", ""), broker)

def normalize_trade(t):
    lots  = parse_lot(t.get("lot", 0))
    price = derive_price(t)
    action = t.get("action", "")
    broker = t.get("buyer", "?") if action == "buy" else t.get("seller", "?")
    btype  = broker_type_short(
        t.get("buyer_type", "") if action == "buy" else t.get("seller_type", "")
    )
    flag = ""
    if lots >= BANDAR_LOT:  flag = "BANDAR"
    elif lots >= LARGE_LOT: flag = "LARGE"

    return {
        "time":   t.get("time", "?"),
        "price":  round(price),
        "lots":   round(lots),
        "action": action,
        "broker": broker,
        "btype":  btype,
        "flag":   flag,
    }

# ─── SIGNAL ENGINE ────────────────────────────────────────────────────────────

def compute_signals(trades):
    """
    trades: list of normalized trade dicts, newest first.
    Returns (signals, stats).
    """
    signals = []

    if len(trades) < 3:
        return signals, {}

    # Buy pressure (rolling BUY_PRESS_N)
    window = trades[:BUY_PRESS_N]
    buy_count  = sum(1 for t in window if t["action"] == "buy")
    sell_count = len(window) - buy_count
    buy_pct    = buy_count / len(window) * 100

    if buy_pct >= 70:
        signals.append({"label": "BULLISH TAPE", "detail": f"{buy_pct:.0f}% buy in last {len(window)}", "color": "#00e676"})
    elif buy_pct <= 30:
        signals.append({"label": "BEARISH TAPE", "detail": f"{buy_pct:.0f}% buy in last {len(window)}", "color": "#ff1744"})

    # Absorption: heavy sell but price flat/up
    if len(trades) >= ABS_WINDOW:
        last_n   = trades[:ABS_WINDOW]
        sell_lots = sum(t["lots"] for t in last_n if t["action"] == "sell")
        prices    = [t["price"] for t in last_n if t["price"] > 0]
        if sell_lots >= 1000 and len(prices) >= 2 and prices[0] >= prices[-1]:
            signals.append({"label": "ABSORPTION", "detail": f"{sell_lots:,} sell lots but price held/up", "color": "#ffd740"})

    # Bandar activity: big lot in last 10
    if any(t["flag"] == "BANDAR" for t in trades[:10]):
        biggest = max((t["lots"] for t in trades[:10] if t["flag"] == "BANDAR"), default=0)
        signals.append({"label": "BANDAR LOT", "detail": f"≥{biggest:,} lots in last 10 trades", "color": "#ff6d00"})

    # Momentum: consecutive price direction
    prices = [t["price"] for t in trades[:MOM_WINDOW] if t["price"] > 0]
    if len(prices) >= MOM_WINDOW:
        if all(prices[i] > prices[i+1] for i in range(len(prices)-1)):
            signals.append({"label": "MOMENTUM UP", "detail": f"{len(prices)} consecutive higher prices", "color": "#00e676"})
        elif all(prices[i] < prices[i+1] for i in range(len(prices)-1)):
            signals.append({"label": "MOMENTUM DOWN", "detail": f"{len(prices)} consecutive lower prices", "color": "#ff1744"})

    stats = {
        "buy_pct":    round(buy_pct, 1),
        "buy_count":  buy_count,
        "sell_count": sell_count,
        "window":     len(window),
        "last_price": trades[0]["price"] if trades else 0,
    }
    return signals, stats

# ─── POLLER ──────────────────────────────────────────────────────────────────

class ScalpPoller(threading.Thread):
    def __init__(self, symbol):
        super().__init__(daemon=True)
        self.symbol  = symbol.upper()
        self.running = True
        self._seen   = set()   # dedup keys
        self._buffer = deque(maxlen=BUFFER_SIZE)

    def run(self):
        while self.running:
            try:
                self._poll()
            except urllib.error.HTTPError as e:
                with _state_lock:
                    _state[self.symbol] = _state.get(self.symbol, {})
                    if e.code == 401:
                        _state[self.symbol]["error"] = "TOKEN EXPIRED — refresh via Stockbit Token Sync"
                    else:
                        _state[self.symbol]["error"] = f"HTTP {e.code}"
            except Exception as e:
                with _state_lock:
                    _state[self.symbol] = _state.get(self.symbol, {})
                    _state[self.symbol]["error"] = str(e)[:80]
            time.sleep(POLL_INTERVAL)

    def _poll(self):
        data   = api_get("/order-trade/running-trade", {
            "symbols[]": self.symbol,
            "sort":      "DESC",
            "limit":     100,
            "order_by":  "RUNNING_TRADE_ORDER_BY_TIME",
        })
        raw_trades = data.get("data", {}).get("running_trade", [])
        raw_trades = [t for t in raw_trades if t.get("market_board") == "RG"]

        new_count = 0
        for t in raw_trades:
            key = trade_key(t)
            if key not in self._seen:
                self._seen.add(key)
                self._buffer.appendleft(normalize_trade(t))
                new_count += 1

        # cap seen set to avoid unbounded growth (keep last 500 keys)
        if len(self._seen) > 500:
            self._seen = set(list(self._seen)[-300:])

        trades  = list(self._buffer)
        signals, stats = compute_signals(trades)

        with _state_lock:
            _state[self.symbol] = {
                "trades":      trades[:100],  # send latest 100 to browser
                "signals":     signals,
                "stats":       stats,
                "last_update": time.strftime("%H:%M:%S"),
                "new_count":   new_count,
                "error":       None,
            }

    def stop(self):
        self.running = False

# ─── HTML PAGE ────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Scalp Monitor</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0d1117; color: #c9d1d9; font-family: 'SF Mono', Consolas, monospace; font-size: 13px; padding: 16px; }
h1 { color: #58a6ff; font-size: 1.2em; margin-bottom: 12px; }
.controls { display: flex; gap: 10px; align-items: center; margin-bottom: 14px; flex-wrap: wrap; }
input[type=text] { background: #161b22; border: 1px solid #30363d; color: #c9d1d9; padding: 7px 10px; border-radius: 6px; font-family: inherit; font-size: 13px; width: 120px; text-transform: uppercase; }
button { background: #1f6feb; color: #fff; border: none; padding: 7px 14px; border-radius: 6px; cursor: pointer; font-family: inherit; font-size: 13px; }
button:hover { background: #388bfd; }
.status { color: #8b949e; font-size: .85em; }
.signals { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; min-height: 32px; }
.signal { padding: 4px 10px; border-radius: 4px; font-size: .82em; font-weight: bold; background: #161b22; }
.stats-bar { display: flex; gap: 16px; margin-bottom: 12px; font-size: .85em; color: #8b949e; flex-wrap: wrap; }
.stats-bar span { color: #c9d1d9; }
.buy-bar-wrap { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; }
.buy-bar-bg { background: #ff1744; border-radius: 3px; height: 10px; width: 200px; }
.buy-bar-fill { background: #00e676; border-radius: 3px; height: 10px; transition: width .4s; }
table { border-collapse: collapse; width: 100%; }
th { background: #161b22; color: #8b949e; padding: 6px 9px; text-align: left; font-size: .8em; font-weight: 600; position: sticky; top: 0; border-bottom: 1px solid #30363d; }
td { padding: 5px 9px; border-bottom: 1px solid #21262d; font-size: .82em; }
tr.buy td { color: #c9d1d9; }
tr.sell td { color: #8b949e; }
tr.buy td.action { color: #00e676; font-weight: bold; }
tr.sell td.action { color: #ff1744; font-weight: bold; }
tr.large { background: #1a1600; }
tr.large td.lots { color: #ffd740; font-weight: bold; }
tr.bandar { background: #1a0a00; }
tr.bandar td.lots { color: #ff6d00; font-weight: bold; font-size: 1.1em; }
tr.bandar td { border-left: 3px solid #ff6d00; }
.error { color: #ff1744; margin-top: 8px; }
.new-badge { background: #00e676; color: #0d1117; border-radius: 3px; padding: 0 4px; font-size: .7em; font-weight: bold; }
</style>
</head>
<body>
<h1>Scalp Monitor — IDX Live Tape</h1>

<div class="controls">
  <input type="text" id="sym" placeholder="e.g. BBCA" maxlength="6">
  <button onclick="startWatch()">Watch</button>
  <button onclick="stopWatch()" style="background:#30363d">Stop</button>
  <span class="status" id="status">Enter a symbol and click Watch.</span>
</div>

<div class="signals" id="signals"></div>

<div class="stats-bar" id="statsbar"></div>

<div class="buy-bar-wrap">
  <span style="color:#00e676;font-size:.8em">BUY</span>
  <div class="buy-bar-bg"><div class="buy-bar-fill" id="buybar" style="width:50%"></div></div>
  <span style="color:#ff1744;font-size:.8em">SELL</span>
  <span id="buypct" style="margin-left:8px;color:#8b949e;font-size:.8em">—</span>
</div>

<table>
  <thead>
    <tr>
      <th>TIME</th><th>PRICE</th><th>LOTS</th><th>B/S</th><th>BROKER</th><th>TYPE</th><th>FLAG</th>
    </tr>
  </thead>
  <tbody id="tape"></tbody>
</table>

<div class="error" id="errmsg"></div>

<script>
let watchSymbol = null;
let pollTimer   = null;
let prevCount   = 0;

function startWatch() {
  const sym = document.getElementById('sym').value.trim().toUpperCase();
  if (!sym) return;
  if (watchSymbol !== sym) prevCount = 0;
  watchSymbol = sym;
  document.getElementById('status').textContent = 'Connecting to ' + sym + '...';
  clearInterval(pollTimer);
  fetch('/watch/' + sym);  // tell server to start polling
  pollTimer = setInterval(poll, 3000);
  poll();
}

function stopWatch() {
  clearInterval(pollTimer);
  pollTimer = null;
  document.getElementById('status').textContent = 'Stopped.';
}

function poll() {
  if (!watchSymbol) return;
  fetch('/api/' + watchSymbol)
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        document.getElementById('errmsg').textContent = '⚠ ' + data.error;
        return;
      }
      document.getElementById('errmsg').textContent = '';
      renderSignals(data.signals);
      renderStats(data.stats, data.last_update, data.new_count);
      renderTape(data.trades, data.new_count);
    })
    .catch(e => {
      document.getElementById('status').textContent = 'Server unreachable — is scalp_server.py running?';
    });
}

function renderSignals(signals) {
  const el = document.getElementById('signals');
  if (!signals || signals.length === 0) {
    el.innerHTML = '<span style="color:#484f58;font-size:.8em">No active signals</span>';
    return;
  }
  el.innerHTML = signals.map(s =>
    `<div class="signal" style="color:${s.color};border:1px solid ${s.color}40">
       ${s.label} <span style="color:#8b949e;font-weight:normal">${s.detail}</span>
     </div>`
  ).join('');
}

function renderStats(stats, lastUpdate, newCount) {
  if (!stats) return;
  const badge = newCount > 0 ? `<span class="new-badge">+${newCount}</span>` : '';
  document.getElementById('statsbar').innerHTML =
    `<span>Updated: <span>${lastUpdate}</span> ${badge}</span>` +
    `<span>Buy: <span style="color:#00e676">${stats.buy_count}</span> / Sell: <span style="color:#ff1744">${stats.sell_count}</span> (last ${stats.window})</span>` +
    `<span>Last price: <span>${stats.last_price ? stats.last_price.toLocaleString() : '—'}</span></span>`;

  const pct = stats.buy_pct || 50;
  document.getElementById('buybar').style.width = pct + '%';
  document.getElementById('buypct').textContent = pct.toFixed(1) + '% buy';
  document.getElementById('status').textContent = 'Watching ' + watchSymbol;
}

function renderTape(trades, newCount) {
  if (!trades || !trades.length) return;
  const tbody = document.getElementById('tape');
  const rows = trades.map((t, i) => {
    const rowClass = t.flag === 'BANDAR' ? 'bandar' : t.flag === 'LARGE' ? 'large' : t.action;
    const isNew = i < newCount;
    return `<tr class="${rowClass}">
      <td>${t.time}${isNew ? ' <span class="new-badge">NEW</span>' : ''}</td>
      <td>${t.price ? t.price.toLocaleString() : '—'}</td>
      <td class="lots">${t.lots.toLocaleString()}</td>
      <td class="action">${t.action.toUpperCase()}</td>
      <td>${t.broker}</td>
      <td>${t.btype}</td>
      <td>${t.flag ? '<b style="color:#ff6d00">' + t.flag + '</b>' : ''}</td>
    </tr>`;
  });
  tbody.innerHTML = rows.join('');
}
</script>
</body>
</html>"""

# ─── HTTP HANDLER ─────────────────────────────────────────────────────────────

class ScalpHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress default request logs

    def send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")

        if path == "" or path == "/":
            self.send_html(HTML)
            return

        if path.startswith("/watch/"):
            symbol = path.split("/watch/")[-1].upper()
            _ensure_poller(symbol)
            self.send_json({"ok": True})
            return

        if path.startswith("/api/"):
            symbol = path.split("/api/")[-1].upper()
            _ensure_poller(symbol)
            with _state_lock:
                data = _state.get(symbol, {"error": "No data yet — polling started", "trades": [], "signals": [], "stats": {}, "last_update": "—", "new_count": 0})
            self.send_json(data)
            return

        self.send_response(404)
        self.end_headers()

# ─── POLLER MANAGEMENT ────────────────────────────────────────────────────────

def _ensure_poller(symbol):
    with _state_lock:
        if symbol not in _pollers or not _pollers[symbol].is_alive():
            print(f"  Starting poller for {symbol}")
            p = ScalpPoller(symbol)
            p.start()
            _pollers[symbol] = p

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    try:
        load_token()
    except Exception as e:
        print(f"✗ Cannot read token from {CONFIG_PATH}: {e}")
        print("  Refresh via Stockbit Token Sync extension first.")
        sys.exit(1)

    server = HTTPServer(("localhost", PORT), ScalpHandler)
    print(f"Scalp Monitor running at http://localhost:{PORT}/")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
