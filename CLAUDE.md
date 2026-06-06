# CLAUDE.md — Template

Copy this to CLAUDE.md and fill in your details. This file is read by Claude Code at session start.

---

## Who I Am

- **Name:** YOUR_NAME
- **Level:** (e.g. newbie swing trader / intermediate / experienced)
- **Style:** Swing trading, ~3-day holds. Long only — IDX does not allow retail short selling.
- **Market:** IDX (Indonesia Stock Exchange)
- **Broker:** Stockbit
- **Known weakness:** (e.g. exit timing, position sizing, chasing pumps)

---

## TradingView MCP Setup

- TradingView Desktop app running, connected via MCP at `~/tradingview-mcp`
- Check connection: `mcp__tradingview__tv_health_check`
- Always use **Daily (D) timeframe** for swing trade analysis

### Known MCP Quirks

**pine_open fails** with "Could not open Pine Editor" — use `ui_open_panel(panel="pine-editor", action="open")` first, then `pine_set_source`.

**Opening screener panel:** if `[data-name="screener-topbar-screen-title"]` returns null, find and click the Screeners button first:
```javascript
const btns = Array.from(document.querySelectorAll('button,[role="button"]'));
const btn = btns.find(b => b.getAttribute('aria-label')?.toLowerCase().includes('screener'));
if (btn) btn.click();
```

---

## Files in This Repository

| File | Purpose |
|------|---------|
| `wyckoff_ichimoku_idx_analyzer.pine` | Chart overlay indicator. Save in TradingView as **"Wyckoff_ichimoku analyzer 1"** |
| `wyckoff_ichimoku_break21_analyzer.pine` | Combined Wyckoff + Ichimoku + Break 21 overlay. Save as **"Wyckoff + Ichimoku + Break 21 Analyzer"** |
| `volume_distribution_analyzer.pine` | VDA bottom panel. Save in TradingView as **"Volume Distribution Analysis"** |
| `bandar_dashboard.py` | **Bandar Intelligence Dashboard** — batch screener + quality gate + broker flow → HTML output |
| `scalp_server.py` | **Scalp Monitor** — live tape reader. Run: `python3 scalp_server.py` → http://localhost:8765/ |
| `screener_workflow_guide.md` | Full daily workflow — read this |
| `SETUP.md` | Setup guide for new machine |
| `CLAUDE.md` | This file |

---

## Two Screeners (must be saved in TradingView)

### Screener 1: "IDX Accumulation"
- Exchange: IDX, Type: Stock, Price > 100
- Avg Volume (30d) > 10,000,000
- Relative Volume < 0.6
- RSI (14) between 38–52
- Sort: Rel Vol ascending

### Screener 2: "Erick Volum + Trend" (rename to your own name)
- Exchange: IDX, Type: Stock, Price > 100
- EMA(89) < Close, RSI(21) > 54
- Rel Vol > 1.0, Price × Vol > 5,000,000,000
- Sort: Rel Vol descending

---

## Pine Script Indicators (TradingView names must match exactly)

- `wyckoff_ichimoku_idx_analyzer.pine` → saved as **"Wyckoff_ichimoku analyzer 1"**
- `volume_distribution_analyzer.pine` → saved as **"Volume Distribution Analysis"**

For ad-hoc chart checks:
`chart_set_symbol` → `chart_set_timeframe("D")` → `data_get_ohlcv(summary=true, count=30)` → `data_get_pine_tables("Wyckoff_ichimoku analyzer 1")` → `data_get_pine_tables("Volume Distribution Analysis")`

---

## Trigger Phrases

| Say | Claude does |
|-----|-------------|
| `morning market check` | Full scan: Screener 2 + SC Watch + chart check + broker flow + news |
| `evening analysis` | Sealed candle review: LPS flag + SC Watch update + Screener 1 check |

---

## Entry System

### 2-Lock Entry
- **Lock 1 — Ichimoku:** Price above cloud AND Tenkan > Kijun AND Chikou bullish
- **Lock 2 — Wyckoff:** SoS, Spring, or NS signal in last 1–3 bars
- **Exception:** Springs can fire below cloud — only need TK > KJ

### Entry Rules
- Spring → buy next morning open
- SoS → wait for LPS (first NS bar 1–3 days after). Never buy the SoS bar.
- NS above cloud → buy at current price

### Exit
Turtle trader approach — hold until EXIT SIGNAL fires (TK crossunder / Upthrust / high-vol bear). No fixed % target.

### Stop Loss
- Below consolidation zone low (dashboard "Stop Loss Guide"), max 5% below entry
- Place in Stockbit broker **immediately** after entry — not a mental stop

---

## SC Watch
Stored in `trading_journal.md` — SC Watch table at top. Not a TradingView watchlist.
- Add when SC/Spring/EVR appears (even below cloud)
- Graduate to buy list only when cloud breakout + 2-Lock confirmed
- Remove when SC Low breaks on high volume

---

## Bandar Intelligence Dashboard

Standalone Python script that runs the full IDX screening pipeline automatically.

**Run:** `python3 bandar_dashboard.py` → opens `bandar_dashboard.html` in browser
**Token:** reads from `stockbit-mcp/config.json` — refresh via Token Sync extension before running

**What it does:**
1. Pulls Stockbit bandar screener + foreign flow screener
2. Scores each candidate using the Conviction Scoring System (auto-computable max 5/9)
3. Quality gates stocks scoring ≥2 (Piotroski ≥7, Altman >2, net margin >0)
4. Pulls broker distribution (today + 3-month trend) for stocks passing quality gate
5. Generates HTML dashboard sorted by score

**Score interpretation:** ≥5 → SC Watch candidate · 3–4 → Monitor · <3 → Pass
**Wyckoff/Ichimoku (+4) is NOT auto-computed** — still requires manual chart check.

---

## Scalp Monitor

Live tape reader for intraday analysis. Rule-based signals only — no AI in the hot path.

**Run:** `python3 scalp_server.py` → open `http://localhost:8765/`
**Token:** same `stockbit-mcp/config.json` — no separate setup needed

Enter a symbol and click Watch. Tape polls every 3 seconds.

**Signals:**

| Signal | Condition |
|--------|-----------|
| BULLISH TAPE | >70% buy in last 20 trades |
| BEARISH TAPE | <30% buy in last 20 trades |
| ABSORPTION | ≥1000 sell lots in last 5 trades but price flat/up |
| BANDAR LOT | Single trade ≥2000 lots in last 10 |
| MOMENTUM UP/DOWN | 6 consecutive higher/lower prices |

Tape color: yellow = large lot (≥500), orange border = bandar lot (≥2000).

---

## Stockbit MCP
Eight tools:

*Screeners:*
- `stockbit_screener_bandar(filter, page)` — Bandarmology screener. Verdicts: ACCELERATING / ACCUMULATING / WATCH / DISTRIBUTING
- `stockbit_screener_foreign_flow(period, page)` — Net foreign flow screener
- `stockbit_screener_fundamental(type, page)` — Fundamental ranking screener

*Per-stock:*
- `stockbit_fundamentals(symbol)` — quality gate: Piotroski, Altman Z, margins, momentum
- `stockbit_insider(symbol)` — major shareholder changes from KSEI
- `stockbit_broker_distribution(symbol, date)` — full-day foreign/local net flow. Primary tool.
- `stockbit_delta_summary(symbol, date)` — open vs close session delta
- `stockbit_running_trade(symbol, date)` — raw ticks

Token expires daily. Refresh via Chrome extension → Sync Token to Claude (see SETUP.md).
If 401 error: token expired, refresh it.

---

## Key Rules
1. Never buy below the cloud (except Springs — only need TK > KJ)
2. Never buy the SoS bar. Wait for LPS.
3. Spring is the best entry.
4. Never buy after +20% single-day spike (gorengan).
5. Stop loss in Stockbit immediately after every entry.
6. No signal = no trade. Cash is a position.
7. Check broker flow before entry. Foreign distributing on a BUY SIGNAL = skip.
8. Analyze after 16:15 WIB — sealed candles only.
9. Token expires daily — refresh before each morning scan.
