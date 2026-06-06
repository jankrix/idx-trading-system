#!/usr/bin/env python3
"""
Bandar Intelligence Dashboard v2
Improvements from Opus review (2026-06-05):
  - Fixed affordability bug (now uses 52W Low as proxy + visible range)
  - Added position awareness: [HELD] / [SC WATCH] / [NEW] tags from trading_journal.md
  - Added score delta: persists to bandar_history.json, shows night-over-night changes
  - Added pump auto-flag: 1M > 30% or 1Y > 300% = PUMP WARNING
  - Added insider accumulation signal for score >= 4
  - Shows 52W price range so affordability is visible
  - SC Watch proposals printed to stdout

Schedule: weekdays 16:20 WIB via launchd (com.erick.bandar-dashboard)
Run:      python3 bandar_dashboard.py
Token:    reads stockbit-mcp/config.json (refresh via Token Sync extension)
"""

import json, time, random, sys, re
import urllib.request, urllib.parse, urllib.error
import datetime
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────────

SCRIPT_DIR   = Path(__file__).parent
CONFIG_PATH  = SCRIPT_DIR.parent / "stockbit-mcp/config.json"
OUTPUT_PATH  = SCRIPT_DIR / "bandar_dashboard.html"
HISTORY_PATH = SCRIPT_DIR / "bandar_history.json"
JOURNAL_PATH = SCRIPT_DIR / "trading_journal.md"
BASE_HOST    = "exodus.stockbit.com"

BANDAR_PAGES    = 4
FOREIGN_PAGES   = 2
MIN_SCORE_DEEP  = 2    # quality gate + broker for score >= this
MIN_SCORE_DEEP_INSIDER = 4  # also fetch insider for score >= this
GORENGAN        = {"DFAM"}
PUMP_1M_THRESH  = 30.0   # % — flag if 1M return exceeds this
PUMP_1Y_THRESH  = 300.0  # % — flag if 1Y return exceeds this

def load_token():
    return json.loads(CONFIG_PATH.read_text())["bearer_token"]

def sleep_polite():
    time.sleep(0.5 + random.random() * 0.4)

# ─── HTTP ─────────────────────────────────────────────────────────────────────

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
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("  ✗ TOKEN EXPIRED — refresh via Stockbit Token Sync extension")
            sys.exit(1)
        raise

# ─── JOURNAL STATE ────────────────────────────────────────────────────────────

def load_journal_state():
    """Parse trading_journal.md for held positions and SC Watch symbols."""
    held, sc_watch = set(), set()
    try:
        content = JOURNAL_PATH.read_text(encoding="utf-8")
        # Open Positions: look for ### TICKER lines
        in_pos = False
        for line in content.split("\n"):
            if "## Open Positions" in line:
                in_pos = True
            elif line.startswith("## ") and in_pos:
                in_pos = False
            elif in_pos and line.startswith("### "):
                sym = line.replace("###", "").strip().split()[0].split("—")[0].strip()
                if re.match(r"^[A-Z]{2,5}$", sym):
                    held.add(sym)
        # SC Watch table: | TICKER | ...
        in_sc = False
        for line in content.split("\n"):
            if "## SC Watch" in line:
                in_sc = True
            elif line.startswith("## ") and in_sc and "SC Watch" not in line:
                in_sc = False
            elif in_sc and "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2:
                    sym = parts[1]
                    if re.match(r"^[A-Z]{2,5}$", sym):
                        sc_watch.add(sym)
    except Exception as e:
        print(f"  Warning: journal parse error: {e}")
    return held, sc_watch

# ─── SCORE HISTORY ────────────────────────────────────────────────────────────

def load_history():
    try:
        return json.loads(HISTORY_PATH.read_text())
    except:
        return {}

def save_history(results):
    history = load_history()
    today = datetime.date.today().isoformat()
    history[today] = {r["symbol"]: r["score"] for r in results if r["score"] >= 0}
    # Keep 7 days
    for old in sorted(history.keys())[:-7]:
        del history[old]
    HISTORY_PATH.write_text(json.dumps(history, indent=2))
    return history

def score_delta(symbol, current_score, history):
    dates = sorted(history.keys())
    today = datetime.date.today().isoformat()
    past = [d for d in dates if d < today]
    if not past:
        return None
    prev_scores = history.get(past[-1], {})
    if symbol in prev_scores:
        return current_score - prev_scores[symbol]
    return None

# ─── SCREENERS ───────────────────────────────────────────────────────────────

def fetch_bandar_screener(pages=4):
    stocks = []
    for page in range(1, pages + 1):
        data = api_get("/screener/templates/96", {
            "type": "TEMPLATE_TYPE_GURU", "page": page, "limit": 25
        })
        calcs = data.get("data", {}).get("calcs", [])
        if not calcs:
            break
        for c in calcs:
            m = {r["item"]: r for r in c.get("results", [])}
            def raw(key):
                try: return float(m[key].get("raw", 0) or 0)
                except: return 0.0
            def disp(key):
                try: return m[key].get("display", "N/A")
                except: return "N/A"

            bv   = raw("Bandar Value")
            pv   = raw("Previous Bandar Value")
            ma10 = raw("Bandar Value MA 10")
            ma20 = raw("Bandar Value MA 20")

            if bv > pv and bv > ma10 and bv > ma20:
                verdict = "ACCELERATING"
            elif bv > pv and bv > ma20:
                verdict = "ACCUMULATING"
            elif bv > pv:
                verdict = "WATCH"
            else:
                verdict = "DISTRIBUTING"

            stocks.append({
                "symbol":       c["company"]["symbol"],
                "name":         c["company"]["name"],
                "bandar_value": disp("Bandar Value"),
                "bandar_raw":   bv,
                "verdict":      verdict,
            })
        sleep_polite()
        is_more = data.get("data", {}).get("is_more")
        if is_more is False or (is_more is None and len(calcs) < 25):
            break
    return stocks


def fetch_foreign_flow(pages=2):
    stocks = []
    for page in range(1, pages + 1):
        data = api_get("/screener/templates/80", {
            "type": "TEMPLATE_TYPE_GURU", "page": page, "limit": 25
        })
        calcs = data.get("data", {}).get("calcs", [])
        if not calcs:
            break
        for c in calcs:
            results = c.get("results", [])
            if not results:
                continue
            first = results[0]
            try: raw_val = float(first.get("raw", 0) or 0)
            except: raw_val = 0.0
            stocks.append({
                "symbol":          c["company"]["symbol"],
                "net_foreign":     first.get("display", "N/A"),
                "net_foreign_raw": raw_val,
            })
        sleep_polite()
        is_more = data.get("data", {}).get("is_more")
        if is_more is False or (is_more is None and len(calcs) < 25):
            break
    return stocks

# ─── FUNDAMENTALS ────────────────────────────────────────────────────────────

def fetch_fundamentals(symbol):
    data = api_get(f"/keystats/ratio/v1/{symbol.upper()}", {"year_limit": 10})
    groups = data.get("data", {}).get("closure_fin_items_results", [])
    flat = {}
    for g in groups:
        for e in g.get("fin_name_results", []):
            item = e.get("fitem", {})
            name, val = item.get("name"), item.get("value")
            if name and val:
                flat[name] = val

    def num(key):
        v = flat.get(key)
        if v is None: return None
        raw = v.get("raw") if isinstance(v, dict) else v
        try: return float(str(raw).replace(",", "").replace("%", "").strip())
        except: return None

    p  = num("Piotroski F-Score")
    z  = num("Altman Z-Score (Modified)")
    m  = num("Net Profit Margin (Quarter)")
    lo = num("52 Week Low")
    hi = num("52 Week High")
    r1m = num("1 Month Price Returns")
    r1y = num("1 Year Price Returns")

    passes = p is not None and p >= 7 and z is not None and z > 2 and m is not None and m > 0

    if p is None or p < 7:
        kill = f"Piotroski {p}" if p is not None else "Piotroski N/A"
    elif z is None or z <= 2:
        kill = f"Altman {z:.2f}" if z is not None else "Altman N/A"
    elif m is None or m <= 0:
        kill = f"Margin {m:.1f}%" if m is not None else "Margin N/A"
    else:
        kill = f"P:{int(p)} Z:{z:.1f} M:{m:.1f}%"

    # Pump detection
    pump = False
    pump_reason = ""
    if r1m is not None and r1m > PUMP_1M_THRESH:
        pump = True
        pump_reason = f"1M +{r1m:.0f}%"
    if r1y is not None and r1y > PUMP_1Y_THRESH:
        pump = True
        pump_reason += (f" 1Y +{r1y:.0f}%" if pump_reason else f"1Y +{r1y:.0f}%")

    # Affordability: use 52W Low as conservative proxy (real price may be higher)
    affordable_proxy = lo is not None and lo <= 3000

    return {
        "piotroski":        p,
        "altman":           z,
        "net_margin":       m,
        "passes_quality":   passes,
        "kill_reason":      kill,
        "price_52w_low":    lo,
        "price_52w_high":   hi,
        "ret_1m":           r1m,
        "ret_1y":           r1y,
        "pump":             pump,
        "pump_reason":      pump_reason,
        "affordable_proxy": affordable_proxy,
    }

# ─── INSIDER ─────────────────────────────────────────────────────────────────

def fetch_insider_signal(symbol):
    """Return list of recent buyer names if major shareholders are accumulating."""
    try:
        data = api_get("/insider/company/majorholder", {
            "symbols": symbol.upper(),
            "page": 1, "limit": 10,
            "action_type": "ACTION_TYPE_UNSPECIFIED",
            "source_type": "SOURCE_TYPE_UNSPECIFIED",
        })
        movements = data.get("data", {}).get("movements", [])
        buyers = []
        for m in movements[:10]:
            action = m.get("action", "").lower()
            if any(w in action for w in ("buy", "increase", "tambah", "beli")):
                name = m.get("holder_name", "?")
                pct  = m.get("change_percentage", "")
                buyers.append(f"{name} {pct}".strip())
        return buyers[:3] if buyers else None
    except:
        return None

# ─── BROKER ──────────────────────────────────────────────────────────────────

def get_latest_session_date():
    try:
        data = api_get("/order-trade/broker/distribution", {
            "symbol": "BBCA", "investor_type": "INVESTOR_TYPE_ALL",
            "market_board": "MARKET_TYPE_REGULER",
            "data_type": "BROKER_DISTRIBUTION_DATA_TYPE_VALUE",
            "period": "TB_PERIOD_LAST_1_DAY",
        })
        return data.get("data", {}).get("date_info") or data.get("data", {}).get("start_date") or ""
    except:
        return (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")


def fetch_broker(symbol, period="TB_PERIOD_LAST_1_DAY", date=None):
    return api_get("/order-trade/broker/distribution", {
        "symbol":        symbol.upper(),
        "investor_type": "INVESTOR_TYPE_ALL",
        "market_board":  "MARKET_TYPE_REGULER",
        "data_type":     "BROKER_DISTRIBUTION_DATA_TYPE_VALUE",
        "period":        period,
        "date":          date or "",
    })


def parse_broker(raw_data):
    by_value = raw_data.get("data", {}).get("by_value", {})
    buyers   = by_value.get("top_broker_buy", [])
    sellers  = by_value.get("top_broker_sell", [])

    net = {}
    for b in buyers:
        d = b.get("detail", {})
        code = d.get("code", "?")
        if code not in net:
            net[code] = {"buy": 0, "sell": 0, "type": d.get("type", "?")}
        net[code]["buy"] += float(d.get("amount", 0) or 0)
    for s in sellers:
        d = s.get("detail", {})
        code = d.get("code", "?")
        if code not in net:
            net[code] = {"buy": 0, "sell": 0, "type": d.get("type", "?")}
        net[code]["sell"] += float(d.get("amount", 0) or 0)

    bl = sorted(
        [{"broker": k, "type": v["type"], "net": v["buy"] - v["sell"]} for k, v in net.items()],
        key=lambda x: -x["net"]
    )
    fn_b = sum(b["net"] for b in bl if b["type"] == "Asing") / 1e9

    if fn_b > 1:    verdict = "STRONG ACCUM"
    elif fn_b > 0:  verdict = "ACCUM"
    elif fn_b < -1: verdict = "STRONG DIST"
    else:           verdict = "DIST"

    def fmt(b):
        return f"{b['broker']}({b['type'][0] if b['type'] else '?'}) {b['net']/1e9:+.2f}B"

    return {
        "foreign_net_b": fn_b,
        "verdict":       verdict,
        "accumulators":  [fmt(b) for b in bl if b["net"] > 0][:5],
        "distributors":  [fmt(b) for b in bl if b["net"] < 0][-5:],
    }

# ─── SCORING ─────────────────────────────────────────────────────────────────

def score_stock(symbol, bandar_verdict, net_foreign_raw, fund, insider=None):
    if symbol in GORENGAN:
        return -1, ["GORENGAN — never trade"]

    score, notes = 0, []

    if bandar_verdict == "ACCELERATING":
        score += 2; notes.append("Bandar ACCELERATING +2")
    elif bandar_verdict == "ACCUMULATING":
        score += 1; notes.append("Bandar ACCUMULATING +1")

    if net_foreign_raw > 0:
        score += 1; notes.append("Foreign 1M positive +1")

    if fund:
        if fund["passes_quality"]:
            score += 1; notes.append(f"Quality ✓ {fund['kill_reason']} +1")
        else:
            notes.append(f"Quality ✗ {fund['kill_reason']}")

        # Affordability: 52W Low as proxy — flag as approximate
        if fund["affordable_proxy"]:
            score += 1; notes.append(f"52W Low ≤3000 IDR +1 (verify current price)")
        elif fund["price_52w_low"] is not None:
            notes.append(f"52W Low {fund['price_52w_low']:,.0f} — may not fit account")

        if fund["pump"]:
            notes.append(f"⚠ PUMP WARNING: {fund['pump_reason']}")

    if insider:
        notes.append(f"Insider buying: {', '.join(insider[:2])}")

    notes.append("Wyckoff+Ichimoku: +4 potential (needs chart)")
    return score, notes

# ─── HTML ─────────────────────────────────────────────────────────────────────

def _cs(s):
    if s >= 5: return "#00e676"
    if s >= 3: return "#ffab00"
    return "#546e7a"

def _cv(v):
    v = v.upper()
    if "STRONG ACCUM" in v or "ACCELERATING" in v: return "#00e676"
    if "ACCUM" in v or "ACCUMULATING" in v:         return "#69f0ae"
    if "STRONG DIST" in v or "DISTRIBUTING" in v:   return "#ff1744"
    if "DIST" in v:                                  return "#ff6d00"
    if "WATCH" in v:                                 return "#ffd740"
    return "#78909c"

def _cf(n): return "#00e676" if n > 0 else "#ff6d00" if n < 0 else "#78909c"

def generate_html(results, run_time, held, sc_watch_syms, history):
    rows = []
    for r in sorted(results, key=lambda x: -x["score"]):
        sym   = r["symbol"]
        score = r["score"]
        if score < 0: continue

        fund  = r.get("fund", {})
        b1d   = r.get("broker_1d")
        b3m   = r.get("broker_3m")
        fn    = r.get("net_foreign_raw", 0)
        delta = score_delta(sym, score, history)

        # Status tag
        if sym in held:
            tag = '<span style="background:#1f6feb;color:#fff;padding:1px 5px;border-radius:3px;font-size:.75em">HELD</span>'
        elif sym in sc_watch_syms:
            tag = '<span style="background:#388e3c;color:#fff;padding:1px 5px;border-radius:3px;font-size:.75em">SC WATCH</span>'
        else:
            tag = '<span style="background:#30363d;color:#8b949e;padding:1px 5px;border-radius:3px;font-size:.75em">NEW</span>'

        # Score delta badge
        delta_html = ""
        if delta is not None and delta != 0:
            dc = "#00e676" if delta > 0 else "#ff6d00"
            delta_html = f' <span style="color:{dc};font-size:.8em">{"▲" if delta > 0 else "▼"}{abs(delta)}</span>'

        # Price range
        price_html = ""
        if fund:
            lo = fund.get("price_52w_low")
            hi = fund.get("price_52w_high")
            r1m = fund.get("ret_1m")
            if lo and hi:
                price_html = f'<small style="color:#546e7a">{lo:,.0f}–{hi:,.0f}</small>'
            if r1m is not None:
                rc = "#00e676" if r1m > 0 else "#ff6d00"
                price_html += f'<br><small style="color:{rc}">1M {r1m:+.1f}%</small>'
            if fund.get("pump"):
                price_html += f'<br><span style="color:#ff1744;font-size:.8em">⚠ PUMP</span>'

        # Quality gate
        qual_html = ""
        if fund:
            c = "#00e676" if fund["passes_quality"] else "#ff6d00"
            qual_html = f'<span style="color:{c};font-size:.8em">{fund["kill_reason"]}</span>'

        # Insider signal
        insider_html = ""
        if r.get("insider"):
            insider_html = f'<br><small style="color:#ffd740">👁 {", ".join(r["insider"][:2])}</small>'

        # Broker today
        b1d_html = '<span style="color:#37474f">—</span>'
        if b1d:
            acc = " · ".join(b1d["accumulators"][:3])
            dis = " · ".join(b1d["distributors"][:3])
            b1d_html = (
                f'<span style="color:{_cv(b1d["verdict"])}">{b1d["verdict"]}</span> '
                f'<span style="color:{_cf(b1d["foreign_net_b"])}">{b1d["foreign_net_b"]:+.2f}B</span><br>'
                f'<small style="color:#00e676">{acc}</small><br>'
                f'<small style="color:#ff6d00">{dis}</small>'
            )

        # Broker 3M
        b3m_html = '<span style="color:#37474f">—</span>'
        if b3m:
            acc3 = " · ".join(b3m["accumulators"][:3])
            dis3 = " · ".join(b3m["distributors"][:3])
            b3m_html = (
                f'<span style="color:{_cv(b3m["verdict"])}">{b3m["verdict"]}</span> '
                f'<span style="color:{_cf(b3m["foreign_net_b"])}">{b3m["foreign_net_b"]:+.2f}B</span><br>'
                f'<small style="color:#00e676">{acc3}</small><br>'
                f'<small style="color:#ff6d00">{dis3}</small>'
            )

        notes = "<br>".join(
            f'<span style="color:#78909c">{n}</span>' for n in r.get("score_notes", [])
        )

        rows.append(f"""
        <tr>
          <td>
            <b style="font-size:1.05em">{sym}</b> {tag}<br>
            <span style="color:#546e7a;font-size:.8em">{r.get('name','')[:22]}</span>
          </td>
          <td style="text-align:center">
            <span style="font-size:1.6em;font-weight:bold;color:{_cs(score)}">{score}</span>
            <span style="color:#546e7a">/9</span>{delta_html}
          </td>
          <td>
            <span style="color:{_cv(r['bandar_verdict'])}">{r['bandar_verdict']}</span><br>
            <small style="color:#546e7a">{r.get('bandar_value','')}</small>
          </td>
          <td style="color:{_cf(fn)}">{fn/1e9:+.2f}B</td>
          <td>{price_html}</td>
          <td>{qual_html}{insider_html}</td>
          <td>{b1d_html}</td>
          <td>{b3m_html}</td>
          <td style="font-size:.75em;line-height:1.6">{notes}</td>
        </tr>""")

    rows_html = "\n".join(rows)
    count_accel  = sum(1 for r in results if r.get("bandar_verdict") == "ACCELERATING")
    count_qual   = sum(1 for r in results if r.get("fund", {}).get("passes_quality"))
    count_watch  = sum(1 for r in results if r["score"] >= 5)
    count_held   = sum(1 for r in results if r["symbol"] in held)
    count_sc     = sum(1 for r in results if r["symbol"] in sc_watch_syms)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Bandar Dashboard {run_time}</title>
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ background:#0d1117; color:#c9d1d9; font-family:'SF Mono',Consolas,monospace; font-size:13px; padding:16px; }}
h1 {{ color:#58a6ff; font-size:1.3em; margin-bottom:4px; }}
.meta {{ color:#8b949e; font-size:.85em; margin-bottom:12px; }}
.stats {{ display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap; }}
.stat {{ background:#161b22; border:1px solid #30363d; border-radius:6px; padding:10px 14px; }}
.stat .n {{ font-size:1.8em; font-weight:bold; }}
.stat .l {{ font-size:.75em; color:#8b949e; }}
table {{ border-collapse:collapse; width:100%; }}
th {{ background:#161b22; color:#8b949e; padding:7px 9px; text-align:left; font-size:.8em; font-weight:600; position:sticky; top:0; border-bottom:1px solid #30363d; }}
td {{ padding:7px 9px; border-bottom:1px solid #21262d; vertical-align:top; }}
tr:hover td {{ background:#161b22; }}
.legend {{ margin-top:12px; font-size:.75em; color:#484f58; }}
</style>
</head>
<body>
<h1>📊 Bandar Intelligence Dashboard v2 &nbsp;
  <a href="http://localhost:8765/" target="_blank"
     style="font-size:.7em;background:#161b22;border:1px solid #30363d;color:#58a6ff;padding:4px 10px;border-radius:5px;text-decoration:none;vertical-align:middle">
    ⚡ Live Tape
  </a>
</h1>
<div class="meta">Generated {run_time} WIB &nbsp;·&nbsp; Score max 5/9 auto · Wyckoff+Ichimoku +4 needs chart · ▲▼ = score delta vs yesterday</div>

<div class="stats">
  <div class="stat"><div class="n" style="color:#00e676">{count_accel}</div><div class="l">ACCELERATING</div></div>
  <div class="stat"><div class="n" style="color:#58a6ff">{count_qual}</div><div class="l">Quality Gate ✓</div></div>
  <div class="stat"><div class="n" style="color:#ffd740">{count_watch}</div><div class="l">Score ≥5</div></div>
  <div class="stat"><div class="n" style="color:#1f6feb">{count_held}</div><div class="l">Held Positions</div></div>
  <div class="stat"><div class="n" style="color:#388e3c">{count_sc}</div><div class="l">SC Watch</div></div>
  <div class="stat"><div class="n" style="color:#8b949e">{len(results)}</div><div class="l">Total</div></div>
</div>

<table>
  <thead>
    <tr>
      <th>Ticker</th><th>Score</th><th>Bandar</th><th>Foreign 1M</th>
      <th>Price Range</th><th>Quality / Insider</th>
      <th>Broker Today</th><th>Broker 3M</th><th>Notes</th>
    </tr>
  </thead>
  <tbody>
{rows_html}
  </tbody>
</table>

<div class="legend">
  Score: <span style="color:#00e676">≥5 SC Watch</span> · <span style="color:#ffab00">3–4 Monitor</span> ·
  <span style="color:#546e7a">&lt;3 Pass</span> &nbsp;|&nbsp;
  Tags: <span style="background:#1f6feb;color:#fff;padding:0 4px">HELD</span>
  <span style="background:#388e3c;color:#fff;padding:0 4px">SC WATCH</span>
  <span style="background:#30363d;color:#8b949e;padding:0 4px">NEW</span> &nbsp;|&nbsp;
  Price range = 52W Low–High (verify current price before entry) &nbsp;|&nbsp;
  Broker (A)=Asing (L)=Lokal (P)=Pemerintah
</div>
</body>
</html>"""

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{run_time}] Bandar Dashboard v2 — starting run")

    # State: journal positions + SC Watch
    held, sc_watch_syms = load_journal_state()
    print(f"  Journal: {len(held)} held positions, {len(sc_watch_syms)} SC Watch: {held or '—'}, {sc_watch_syms or '—'}")

    # History for delta
    history = load_history()

    # Latest session date
    print("  → Latest session date...")
    latest_date = get_latest_session_date()
    print(f"     {latest_date}")

    # Bandar screener
    print("  → Bandar screener...")
    bandar_all = fetch_bandar_screener(BANDAR_PAGES)
    candidates = [s for s in bandar_all
                  if s["verdict"] in ("ACCELERATING", "ACCUMULATING", "WATCH")
                  and s["symbol"] not in GORENGAN]
    print(f"     {len(bandar_all)} total, {len(candidates)} positive")

    # Foreign flow
    print("  → Foreign flow 1M...")
    foreign_all  = fetch_foreign_flow(FOREIGN_PAGES)
    foreign_map  = {s["symbol"]: s for s in foreign_all}
    print(f"     {len(foreign_all)} stocks")

    # Initial scoring
    results = []
    for s in candidates:
        sym = s["symbol"]
        ff  = foreign_map.get(sym, {})
        score, notes = score_stock(sym, s["verdict"], ff.get("net_foreign_raw", 0), None)
        results.append({
            "symbol":          sym,
            "name":            s["name"],
            "bandar_verdict":  s["verdict"],
            "bandar_value":    s["bandar_value"],
            "net_foreign_raw": ff.get("net_foreign_raw", 0),
            "score":           score,
            "score_notes":     notes,
        })

    # Deep analysis
    deep = [r for r in results if r["score"] >= MIN_SCORE_DEEP]
    print(f"  → Deep analysis for {len(deep)} stocks...")

    for r in deep:
        sym = r["symbol"]
        print(f"     {sym}...", end="", flush=True)

        # Fundamentals
        try:
            sleep_polite()
            fund = fetch_fundamentals(sym)
            r["fund"] = fund
            ff = foreign_map.get(sym, {})
            score, notes = score_stock(sym, r["bandar_verdict"], ff.get("net_foreign_raw", 0), fund)
            r["score"]       = score
            r["score_notes"] = notes
            print(f" fund={'✓' if fund['passes_quality'] else '✗'}", end="", flush=True)
            if fund.get("pump"):
                print(f" PUMP⚠", end="", flush=True)
        except Exception as e:
            print(f" fund_err", end="", flush=True)

        # Broker (quality gate passes only)
        if r.get("fund", {}).get("passes_quality", False):
            try:
                sleep_polite()
                r["broker_1d"] = parse_broker(fetch_broker(sym, "TB_PERIOD_LAST_1_DAY"))
                sleep_polite()
                r["broker_3m"] = parse_broker(fetch_broker(sym, "TB_PERIOD_LAST_3_MONTHS", latest_date))
                print(f" broker=✓", end="", flush=True)
            except Exception as e:
                print(f" broker_err", end="", flush=True)

            # Insider for score >= threshold
            if r["score"] >= MIN_SCORE_DEEP_INSIDER:
                try:
                    sleep_polite()
                    ins = fetch_insider_signal(sym)
                    if ins:
                        r["insider"] = ins
                        print(f" insider=✓", end="", flush=True)
                except:
                    pass

        print()

    # Persist history + generate HTML
    history = save_history(results)
    print("  → Generating dashboard...")
    html = generate_html(results, run_time, held, sc_watch_syms, history)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"  ✓ {OUTPUT_PATH}")
    print(f"    file://{OUTPUT_PATH.absolute()}")

    # SC Watch proposals
    sc_candidates = [r for r in results
                     if r["score"] >= 5
                     and r["symbol"] not in sc_watch_syms
                     and r["symbol"] not in held
                     and not r.get("fund", {}).get("pump", False)]
    sc_remove = [sym for sym in sc_watch_syms
                 if any(r["symbol"] == sym and r.get("bandar_verdict") == "DISTRIBUTING"
                        for r in results)]

    print(f"\n  ── SC Watch proposals ──")
    if sc_candidates:
        print(f"  ADD (score ≥5, not held, not pump):")
        for r in sorted(sc_candidates, key=lambda x: -x["score"]):
            d = score_delta(r["symbol"], r["score"], history)
            ds = f" ▲{d}" if d and d > 0 else f" ▼{abs(d)}" if d and d < 0 else ""
            print(f"    {r['symbol']:6s} {r['score']}/9{ds}  {r['bandar_verdict']}")
    else:
        print("  No new SC Watch additions tonight.")

    if sc_remove:
        print(f"  REMOVE (bandar now DISTRIBUTING): {', '.join(sc_remove)}")

if __name__ == "__main__":
    main()
