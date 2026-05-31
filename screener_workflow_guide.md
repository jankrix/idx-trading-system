# IDX Stock Screener Workflow Guide

**Strategy:** Wyckoff + Ichimoku 2-Lock System + VSA Volume Confirmation  
**Market:** IDX — Long only  
**Purpose:** Catch stocks early (accumulation phase) and confirm entry before they fly

---

## The Four-Layer System

| Layer | Tool | When | Purpose |
|-------|------|------|---------|
| 0 | **SC Watchlist** (TradingView watchlist) | Built manually, ongoing | Track stocks showing SC/Spring below cloud — candidates for future breakout |
| 1 | **IDX Accumulation Screener** | Every morning | Find stocks building energy quietly — 5–15 days before breakout |
| 2 | **Erick Volum + Trend Screener** | Every morning | Find stocks already breaking out with momentum |
| 3 | **Wyckoff + Ichimoku + VDA on chart** | For every ticker from layers 0–2 | Confirm entry, read volume intent, set stop loss |

**The goal:** Spot a stock in Screener 1 or SC Watchlist → confirm on chart → enter when it appears in Screener 2 with 2-Lock confirmed.

---

## IDX vs NASDAQ — Key Differences

| Dimension | IDX | NASDAQ |
|-----------|-----|--------|
| **Best timeframe** | Daily (D) only | Daily (D) or 4-Hour (4H) |
| **Why Daily only on IDX** | Low liquidity — intraday volume is too thin and noisy to form reliable signals | Deep institutional liquidity — 4H patterns are clean enough to trade |
| **Wyckoff reliability** | High — lower liquidity means Bandar (Composite Man) leaves clear footprints | High on Daily/4H — patterns visible but noisier than IDX due to HFT |
| **Short selling** | NOT allowed for retail | Allowed |
| **Currency** | IDR (Indonesian Rupiah) | USD |
| **Market hours** | 09:00–16:15 WIB (Mon–Thu), 09:00–16:00 WIB (Fri) | 09:30–16:00 EST (22:30–03:00 WIB next day) |
| **Best analysis time** | After 16:15 WIB (candles sealed) | After 03:00 WIB or before IDX open 08:30–09:00 WIB |
| **Price × Volume filter** | > 5 Billion IDR (enough liquidity to trade) | Not needed — all NASDAQ stocks have deep liquidity |
| **Gorengan risk** | High — stocks can be pumped +20–30% in one day | Low — SEC regulation limits manipulation |
| **Stop loss placement** | In Stockbit broker — place IMMEDIATELY after entry | In your broker immediately after entry |
| **Screener tool** | TradingView built-in Screener (IDX exchange filter) | TradingView built-in Screener (NASDAQ exchange filter) |
| **Accumulation signals** | Clearer and longer — Bandar holds base for weeks | Faster — institutional cycles shorter, base may last only a few days |
| **Volume indicators** | Approximate (no broker-level order flow) | Approximate (same caveat — TradingView does not have full order book) |

**For this workflow: IDX only. NASDAQ analysis uses the same indicators but switch timeframe to 4H and remove the IDR liquidity filter.**

---

## How to Build Screener 1 — IDX Accumulation

**Platform:** TradingView → Screener tab → Stock Screener  
**Save name:** `IDX Accumulation`  
**Target result count:** ~30–35 stocks (if you get 100+, your filters are too loose)

### Filters

| Filter | Operator | Value | Why |
|--------|----------|-------|-----|
| **Exchange** | is | Indonesia (IDX) | IDX stocks only |
| **Type** | is | Stock | Exclude ETFs, funds |
| **Price** | greater than | 100 | Remove penny stocks |
| **Avg Volume (30)** | greater than | 10,000,000 | Filters out micro-caps. TradingView IDX only has 10/30/60/90 day options — use 30 |
| **Relative Volume** | less than | 0.6 | Truly dry volume — sellers gone, not just quiet |
| **RSI (14)** | between | 38 and 52 | Not in freefall (>38), not already extended (<52) |

> **Tight-base check is done on the chart, not the screener.** The Wyckoff dashboard shows **"Accumulation Base: YES (X%)"** — that's your confirmation. Screener 1 just narrows the universe to quiet, low-volume stocks near their lows. Claude checks every result for the actual base quality.

### Columns to Add
Close, Change %, Volume, Relative Volume, RSI (14)

### Sort
**Relative Volume ascending** — driest volume first (most likely in accumulation)

### What You're Looking For
- Relative Volume < 0.4 = extremely dry — Bandar holding price flat, sellers gone
- RSI between 38–52 = stock is quiet, not yet moving
- Wyckoff dashboard "Accumulation Base: YES (X%)" on chart = tight base confirmed

---

## How to Build Screener 2 — Erick Volum + Trend

**Platform:** TradingView → Screener tab → Stock Screener  
**Save name:** `Erick Volum + Trend`  
**Target result count:** 2–10 stocks per day (if you get 20+, market is overheated)

### Filters

| Filter | Operator | Value | Why |
|--------|----------|-------|-----|
| **Exchange** | is | Indonesia (IDX) | IDX stocks only |
| **Type** | is | Stock | Exclude ETFs, funds |
| **Price** | greater than | 100 | Remove penny stocks |
| **EMA (89)** | less than | Close | Price above EMA 89 = medium-term uptrend confirmed |
| **RSI (21)** | greater than | **54** | Catches IDX momentum earlier — IDX stocks move at 52-55 before RSI hits 58 |
| **Relative Volume** | greater than | 1.0 | Above-average activity |
| **Volume × Price** | greater than | 5,000,000,000 | Minimum 5B IDR daily turnover = real liquidity |

> **Changed from v1:** RSI(21) lowered from 58 → 54. On IDX, stocks often start their move at RSI 52-55 due to thin liquidity and step-wise (ARA-to-ARA) price movement. By 58, the first big candle is often already done.

> **Volume × Price in TradingView:** Search for "Money Flow" or "Value Traded". If unavailable, use Volume > 5,000,000 AND Price > 1,000 as a proxy. Claude will manually verify Volume × Close > 5B IDR during chart checks.

### Columns to Add
Close, Change %, EMA (89), RSI (21), Relative Volume, Volume

### Sort
**Relative Volume descending** — highest momentum at top

### After Getting Results — Manual Gorengan Check
Before any chart check, scan the results for:
- Any stock up >20% in the last 5 days? → **Skip immediately** (gorengan, you'd be buying from Bandar)
- Any unfamiliar name with suspiciously high volume? → Check Stockbit for "Papan Pemantauan Khusus" (special monitoring board). If flagged → **Skip** (FCA auction volume, not genuine buying)

The indicator now shows **"FCA BAR — SKIP"** in the dashboard when it detects single-price auction bars.

---

## How to Build SC Watchlist — TradingView Watchlist

**Platform:** TradingView → Watchlist panel (right side)  
**Save name:** `SC Watch`

This is NOT a buy list. It is a monitoring list for stocks that show Selling Climax, Spring, or Secondary Test patterns **below the Ichimoku cloud**. These stocks are too early to buy but may break out in the future.

### How to Create It in TradingView
1. Open TradingView → click the **Watchlist** icon on the right panel
2. Click **+** → **New list**
3. Name it `SC Watch`
4. Add tickers manually when the conditions below are met

### What Triggers Adding a Stock to SC Watch

Add a stock to `SC Watch` when its Daily chart shows **any of these, even below cloud:**

| Trigger | What you see | What it means |
|---------|-------------|---------------|
| **SC bar** | Wide bearish bar, huge volume (2x+), closes in upper half | Panic selling absorbed by Bandar |
| **Spring** | Dips below support, snaps back above same bar | Bandar shook out weak hands |
| **Secondary Test (ST)** | Low-volume retest of SC lows | Selling pressure exhausted |
| **EVR at lows** | High volume + narrow bar near multi-week low | Bandar absorbing quietly |

### What to Do With SC Watch Stocks
- **Every morning (Step 0):** Check pre-market IEP for each stock. If IEP is +5%+ or shows bids at ARA → move to active check list for that day
- **Daily:** Monitor for Spring or SoS signal + cloud crossover. When both appear → enters normal 2-lock flow
- **Remove from SC Watch** when: stock breaks below SC low on high volume (thesis broken) OR it breaks above cloud and enters normal buy workflow

---

## How to Trigger the Automated Morning Scan (Claude)

**Just say: "morning market check"**

No ticker list needed. Open TradingView with the screener panel visible first. Claude will:

**Priority 1 — Actionable today (done first):**
0. Read `trading_journal.md` — flag any open position with status STOP HIT as "CUT AT OPEN"
1. Health check TradingView connection (`tv_health_check`)
2. Read **SC Watch** from `trading_journal.md` — check if any SC Watch stock appears in Screener 2 today (highest conviction)
3. Read **Erick Volum + Trend** screener — all tickers via `ui_evaluate`
4. FCA/suspension check: skip any unfamiliar ticker on Papan Pemantauan Khusus (O=H=L=C bars = FCA)
5. Spawn Haiku news agents in parallel for all Screener 2 + SC Watch tickers
6. Chart check every Screener 2 + SC Watch ticker:
   - `chart_set_symbol` → `chart_set_timeframe("D")` → `data_get_ohlcv(summary, 30)`
   - `data_get_pine_tables("Wyckoff_ichimoku analyzer 1")` → read dashboard
   - `data_get_pine_tables("Volume Distribution Analysis")` → read VDA
   - `stockbit_broker_distribution(symbol, date)` → read full-day foreign/local net flow

**Priority 2 — Watchlist feeding (done after):**
7. Read **IDX Accumulation** screener — all ~35 tickers via `ui_evaluate`
8. Spot-check: for any Screener 1 ticker with Accum Base: YES + Rel Vol < 0.4x → add to SC Watch
9. Flag any Screener 1 ticker appearing in BOTH lists → highest conviction, fast-track to chart check

**Output:**
10. Verdict table — one row per stock (includes Broker Flow column)
11. Auto-add BUY SIGNAL stocks to TradingView watchlist via `watchlist_add`

**Post-holiday rule:** On the first trading day after a 2+ day gap, the indicator shows "POST-GAP — VOL UNRELIABLE" on all bars. Claude will flag all Screener 2 signals that day as "post-holiday — confirm next session before entering."

---

## Morning Check vs Evening Analysis — Key Differences

Run **both** daily. Morning is action-oriented. Evening is prep-oriented.

| Step | Morning (before 09:00 WIB) | Evening (after 16:15 WIB) |
|------|---------------------------|--------------------------|
| **Trigger phrase** | `morning market check` | `evening analysis` |
| **Data** | Yesterday's sealed candles | Today's just-sealed candles |
| **Open positions** | Flag STOP HIT → cut at open | Update unrealized P&L |
| **Screener 2** | Find entries for today | Flag LPS candidates (SoS today → LPS tomorrow) |
| **Broker flow** | Confirm entry conviction before buying | Confirm if today's move was real or a pump |
| **Screener 1** | Spot-check only (deprioritized if S2 has tickers) | **Full check** — more important in evening |
| **SC Watch** | Graduate to buy list if cloud breakout | Add new SC/Spring/EVR candidates from today |
| **Output** | "Buy X at open today" | "Watch X tomorrow, here's tomorrow's buy list" |

### Evening-only rules
- **LPS flag:** any Screener 2 ticker with SoS today + RelVol >3x → mark as LPS candidate. Watch for NS bar 1–3 sessions later.
- **SC Watch additions:** any stock showing SC/Spring/EVR today (even below cloud) → add to SC Watch with SC low noted.
- **Screener 1 priority:** run all 35 tickers in evening. Look for "Accum Base: YES" + Rel Vol <0.4x + broker flow showing accumulation → add to SC Watch.
- **Broker flow on today's SoS:** if foreign was distributing on a SoS bar today → do NOT flag as LPS candidate. The signal is a pump, not accumulation (HATM pattern May 29).

---

## Daily Morning Workflow (Before 9:00 AM)

### Step 0 — Pre-Market ARA Scan (08:30–08:45 WIB)

Open Stockbit **before** any chart. Check SC Watch stocks only:

| Check | Green flag if... | Action |
|-------|-----------------|--------|
| IEP vs yesterday close | IEP up +5% or more | Flag for immediate chart check |
| Pre-market order book | Bids sitting at ARA (ceiling price) | Flag — institutional demand signal |

> **Why this matters:** BRPT and PTRO broke out +20-24% on the open. Their SC Watch entry was there for weeks, but the only way to catch the explosion was bids at ARA in pre-market. The Wyckoff screener alone cannot catch below-cloud breakouts — the ARA check is your only early warning.

> **When you add a stock to SC Watch:** Immediately set a TradingView price alert at the stock's `zone_high` (the consolidation high shown on the chart). When the alert fires intraday, act on it — don't wait for the next morning scan.

### Step 1 — Say "morning market check"

Claude reads both screeners and SC Watch automatically via TradingView MCP. Make sure TradingView is open with the screener panel visible.

### Step 2 — Claude Checks Every Ticker (Automated)

For each ticker Claude will:
1. `chart_set_symbol` → `chart_set_timeframe(D)` → `data_get_ohlcv(summary, 30 bars)`
2. `data_get_pine_tables("Wyckoff_ichimoku analyzer 1")` → read Wyckoff + Ichimoku dashboard
3. `data_get_pine_tables("Volume Distribution Analysis")` → read VDA dashboard
4. `stockbit_broker_distribution(symbol, date)` → read full-day broker flow
5. Apply 2-Lock check + VDA + broker flow confirmation
6. Output one row per stock in the results table below

**Output table format:**

| Ticker | Price | Verdict | Lock 1 | Lock 2 (Signal) | VDA | Broker Flow | Entry | Stop | Action |
|--------|-------|---------|--------|-----------------|-----|-------------|-------|------|--------|

*Lock 1 = Cloud/TK/Chikou. Broker Flow = foreign net IDR + dominant broker.*

### Step 3 — Apply Entry Decision Rules

For each BUY SIGNAL stock in the table:

| Signal type | Entry timing | Stop placement |
|-------------|-------------|----------------|
| **Spring** | Buy at next morning open (same day or next day) | Below Spring low |
| **SoS** | Do NOT buy the SoS bar. Wait for first NS bar 1–3 days later (LPS). | Below pre-SoS base |
| **NS (LPS)** | Buy at or just above current price | Below NS bar low |

Additional checks before entry:
- [ ] Is the stock already up +15–20% from its base? If yes → skip, too late
- [ ] R:R ≥ 1:1.5 minimum (to T2)
- [ ] VDA: no BC warning, OBV not declining
- [ ] Not a gorengan pattern (check avg daily volume, recent spike history)
- [ ] Max 2–3 open positions — if already full, no new entries

### Step 4 — VDA Confirmation

Before entering any stock, check the Volume Distribution Analyzer panel:

| VDA shows | Meaning | Action |
|-----------|---------|--------|
| NS (No Supply Bull) | Low vol + narrow + bullish — safe to enter | Confirm entry |
| ABS (Absorption) | High vol + narrow — Bandar still accumulating | Entry valid |
| SC (Selling Climax) after pullback | Demand absorbing sellers | Entry valid |
| SV (Stopping Volume) | Demand entering on a down bar | Entry valid |
| OBV Rising | Big players are net accumulating | Confirms thesis |
| ND (No Demand) | Buyers absent — avoid | Wait, do not enter |
| BC (Buying Climax) | Smart money distributing into your buy | AVOID |

At least one bullish VDA signal should align with your Wyckoff+Ichimoku read before entering.

### Step 5 — Entry Execution

- Set entry price based on signal type (see Step 3)
- Set stop loss BELOW the consolidation zone low (shown in dashboard as "Stop Loss Guide"), max 5% below entry
- **Exit strategy: turtle trader approach** — hold until EXIT SIGNAL fires (TK crossunder / Upthrust / high-vol bear). No fixed % target. Let winner run until the chart says stop.
- **Place stop loss in Stockbit broker IMMEDIATELY after buying — not a mental stop**

### Step 6 — During Market Hours
- Only monitor open positions
- Do not chase new stocks mid-session — daily signals are only valid after candle close
- If a stock hits stop → cut immediately, market order, no hesitation

### Step 7 — End of Day (After 16:15 WIB)
- This is your **primary analysis time** — all daily candles are now sealed
- Update trading journal with closing prices
- Review: did any Screener 1 / SC Watch stocks show new signals today?
- Update SC Watch: did any stock show SC/Spring today? Add it.
- Remove stocks from SC Watch if thesis broken (breaks below SC low on high volume)
- Prepare tomorrow's ticker list for Step 1

---

## The Entry Flow (Summary)

```
08:30 WIB: Check Stockbit pre-market
  → SC Watch stocks: IEP up 5%+? Bids at ARA? → flag for immediate action
        ↓
MORNING: Say "morning market check"
  (TradingView open + screener panel visible + token server running)
        ↓
Claude reads Screener 2 + SC Watch first (actionable today)
  → news agents fire in parallel
  → per ticker: Wyckoff dashboard + VDA + stockbit_broker_distribution
        ↓
Claude reads Screener 1 (~35 tickers)
  → adds tight-base stocks to SC Watch
  → flags any name in BOTH lists
        ↓
Output table: verdict + entry + stop + broker flow
        ↓
POST-HOLIDAY SESSION? → all signals flagged as unconfirmed, wait one more candle
        ↓
For each BUY SIGNAL — confirm broker flow before entering:
  → Spring?  Buy next morning open. Foreign net positive = strong, local only = weaker.
  → SoS?    Wait for LPS (first NS bar 1–3 days after). Do NOT buy the SoS bar.
  → NS/LPS? Buy now. If foreign net distributing = skip.
        ↓
Enter → stop below zone_low → place in Stockbit IMMEDIATELY
        ↓
Hold until EXIT SIGNAL fires (TK crossunder / Upthrust / high-vol bear)
No fixed % target — turtle trader, let winner run
```

---

## Gorengan Filter — Quick Check Before Any Entry

Before entering any stock, run this 30-second check:

| Question | Gorengan warning if... |
|----------|----------------------|
| Avg daily volume (normal days)? | < 5M shares — too thin, easily pumped |
| Price per share? | < 200 IDR — penny stock risk |
| Last 10 days: any +20%+ single day? | Yes → skip, already pumped |
| Does it have real business / sector story? | No = no fundamental floor |
| Volume spike out of nowhere, no Wyckoff base? | Yes → not accumulation, just pump |

Known gorengan: DFAM — never trade it.

---

## Signal Legend — Wyckoff + Ichimoku IDX Analyzer

### Ichimoku Signals

#### TK — Tenkan Cross Up
**What it is:** The Tenkan-sen (9-period midpoint) crossed ABOVE the Kijun-sen (26-period midpoint).  
**What it means:** Short-term momentum turned bullish. Supporting evidence for Lock 1.  
**What to do:** Not enough alone. Needs cloud confirmation.  
**Color:** Blue label below bar.

#### Cloud Position (dashboard)
- **Above Cloud** — Price above the Ichimoku cloud. Bullish. Required for Lock 1.
- **Inside Cloud** — Price inside the cloud. Uncertain. Wait.
- **Below Cloud** — Price below the cloud. Bearish. Do NOT buy.

#### Chikou Span (dashboard)
- **Bullish** — Today's close is above the price from 26 bars ago. Momentum confirmed.
- **Bearish** — Today's close is below the price 26 bars ago. Momentum weak.
- **Neutral** — In between. Watch and wait.

---

### Wyckoff Signals

#### SoS — Sign of Strength
**What it is:** Price breaks above the recent 15-bar resistance on HIGH volume with a wide bullish bar.  
**What it means:** Bandar pushing price up with conviction. Breakout signal.  
**What to do:** Do NOT buy the SoS bar itself — price already moved. Wait for the first NS or ABS pullback bar 1–3 days later (LPS — Last Point of Support). That is the real entry.  
**Exception:** If the SoS bar is only +2–3% above the base, entering next morning open is acceptable.  
**Color:** Green label above bar.

#### Spring — False Breakdown
**What it is:** Price dips BELOW the recent 15-bar support but closes BACK ABOVE it on the same bar.  
**What it means:** Bandar shook out weak hands then bought at the bottom. The real move is about to start.  
**What to do:** Best signal to act on — buy next morning open. Close is still near the base, so you are not chasing. Stop goes below the Spring low.  
**Color:** Orange label below bar.

#### NS — No Supply
**What it is:** A narrow bar with LOW volume while price is above the 20-period MA, not bearish.  
**What it means:** Sellers are gone. No supply of shares available. When buyers enter, price will move fast.  
**What to do:** Safe, quiet entry. Good for adding after SoS (LPS signal). Buy if cloud and TK are bullish.  
**Note:** The boring signal is the best signal. Boring entries win.  
**Color:** Teal label below bar.

#### SC — Selling Climax
**What it is:** A large bearish bar with HIGH volume where price closes in the upper half of the bar.  
**What it means:** Panic selling peaked. Bandar absorbed all shares at low prices. Potential bottom.  
**What to do:** Do NOT buy immediately. Add to SC Watchlist. Watch for Auto Rally then quiet retest. SC = WATCH, not buy.  
**Color:** Red label below bar.

#### EVR — Effort vs Result (Absorption)
**What it is:** HIGH volume but price barely moves (narrow bar).  
**What it means:** Bandar absorbing supply without moving price. Reversal often follows.  
**What to do:** Near lows in downtrend → add to SC Watchlist. Near highs in uptrend → possible distribution warning. Context matters.  
**Color:** Purple label above bar.

#### UT — Upthrust
**What it is:** Price breaks ABOVE the 15-bar high on high volume but closes BACK below it on a bearish bar.  
**What it means:** Bull trap. Bandar selling into retail buying. Distribution phase likely.  
**What to do:** AVOID. Do not buy. If holding → consider reducing or exiting.  
**Color:** Red label above bar.

---

### Accumulation Base (dashboard)

**"Accumulation Base: YES (X%)"** means the stock's price range over the last 15 bars is X%.

- **2–4%** → Extremely tight. Bandar is deliberately holding price flat. Strong accumulation signal.
- **5–8%** → Tight base. Still valid. Watch for volume to dry up further.
- **NO** → Range is wider than 8%. Either trending or not yet in a base. Do not call it accumulation.

The smaller the %, the more deliberate the base. A 2% range over 15 days on IDX means smart money is in control.

---

### Wyckoff Phases (dashboard)

| Phase label | What is happening | What to do |
|-------------|------------------|-----------|
| **Markup / Trending Up** | Price above cloud + SoS confirmed. Already in markup stage. | Hold or add on NS pullbacks (LPS) |
| **Accumulation / Basing** | Flat base forming + volume drying + SC or EVR visible | Watch — do not enter yet |
| **Markup / Pullback Entry** | Price above cloud + NS signal (quiet dip in uptrend) | Good lower-risk entry opportunity |
| **Distribution / Caution** | Upthrust detected | Avoid — do not buy |
| **Markdown / Avoid** | Price below cloud, selling pressure | Do not buy. Wait. |
| **Transitioning** | Mixed signals, no clear phase | Wait for clarity |

---

### Dashboard Verdict

| Verdict | Meaning | Action |
|---------|---------|--------|
| **BUY SIGNAL** | Above cloud + TK bullish + Chikou bullish + (SoS or Spring or NS) | Enter with proper stop — check VDA first |
| **WATCH / WAIT** | Consolidation forming + SC or EVR visible, not yet above cloud | Monitor, do not enter |
| **CAUTION / AVOID** | Upthrust detected, or below cloud with heavy selling | Stay out |
| **NEUTRAL** | No clear signal | No trade — cash is a position |

---

## Signal Legend — Volume Distribution Analyzer (VDA)

The VDA is the **bottom panel** (separate from the price chart). It reads volume behavior to confirm what Bandar is doing.

### The Three Lines

| Line | Color | Meaning |
|------|-------|---------|
| **Vol MA** | Yellow | 20-bar average volume — your baseline |
| **Hi Threshold** | Red | 2x average — institutional activity level |
| **Climax Line** | Orange | 3x average — extreme event (BC or SC) |

### Bar Colors in VDA Panel

| Color | Meaning |
|-------|---------|
| Bright green | Climax bull volume (3x avg) — extreme buying surge |
| Bright red | Climax bear volume (3x avg) — extreme selling or panic |
| Teal | High vol bull (2x avg) — strong demand |
| Pink/red | High vol bear (2x avg) — strong supply |
| Gray | Low volume — market quiet, no conviction |
| Faded teal/red | Normal volume day |

### VDA Labels

| Label | Full Name | What it means | Action |
|-------|-----------|---------------|--------|
| **BC** | Buying Climax | Huge vol + wide bull bar + closes mid — smart money SELLING into retail excitement | Warning: do not buy here |
| **SC** | Selling Climax | Huge vol + wide bear bar + close recovers — smart money ABSORBING panic | Add to SC Watchlist — not buy yet |
| **ABS** | Absorption (EVR) | High vol + narrow bar — Bandar soaking up supply quietly | Bullish if near lows |
| **NS** | No Supply | Low vol + narrow + bullish — sellers exhausted | Safe entry signal |
| **ND** | No Demand | Low vol + narrow + bearish — buyers absent | Avoid, weak market |
| **SV** | Stopping Volume | High vol + wide bear bar + closes near top — demand entering | Potential reversal |

### VDA Dashboard

| Row | What it shows |
|-----|--------------|
| Rel. Volume | Current bar volume vs 20-bar average |
| VSA Signal | Current bar's VSA classification |
| OBV Trend | Is On-Balance Volume rising (accumulation) or declining (distribution)? |
| Effort vs Result | High vol + wide bar = genuine move / High vol + narrow = absorption / Low vol + wide = weak move |
| Close Position | Strong close (top of bar) / weak close (bottom of bar) |
| Volume Trend | Is average volume expanding or contracting over last 5 bars? |

### How VDA and Wyckoff+Ichimoku work together

| Wyckoff+Ichimoku says | VDA confirms | Combined read |
|----------------------|--------------|---------------|
| NS signal | NS or ABS on VDA | High confidence — quiet entry |
| SoS signal | Genuine Move (high vol + wide) | Real breakout, not fake |
| SoS signal | Absorption (high vol + narrow) | Potential fake — be cautious |
| Above cloud, no signal | OBV Rising | Bandar accumulating behind scenes — watch for trigger |
| SC on Wyckoff | SC on VDA | Double confirmation of bottom forming — add to SC Watchlist |
| UT on Wyckoff | BC on VDA | Double distribution warning — stay out |

---

## Stockbit MCP — Running Trade & Broker Flow

### What It Is
A custom MCP server built at `~/Documents/Erick-claude-workspace/brainstorm-digi-product/stockbit-mcp/` that fetches IDX running trade data from Stockbit's internal API. Adds a real broker flow layer on top of the Wyckoff + VDA chart analysis.

### Three Tools Available to Claude

| Tool | What it returns | When to use |
|------|----------------|-------------|
| `stockbit_broker_distribution` | Full-day broker net positions (buy − sell), foreign net flow, dominant Bandar, Wyckoff verdict. **Best tool.** | Every Screener 2 + SC Watch ticker during morning scan |
| `stockbit_delta_summary` | Open session (first 100 trades) vs close session (last 100 trades) delta comparison | When you want to see if buying happened at open vs close |
| `stockbit_running_trade` | Raw tick-by-tick list | Deep inspection of specific bars only |

### How to Read Broker Distribution Output

**Broker types:**
- `Asing` = Foreign broker. This is smart money on IDX. Foreign net buying = real accumulation.
- `Lokal` = Local/domestic broker. Mix of retail and local institutions.
- `Pemerintah` = Government-linked broker (state pension funds, SOE). Usually long-term holders.

**The verdict logic:**
| Verdict | Meaning |
|---------|---------|
| STRONG ACCUMULATION | Foreign net buyers >1B IDR |
| ACCUMULATION | Foreign net buyers |
| STRONG DISTRIBUTION | Foreign net sellers >1B IDR |
| DISTRIBUTION | Foreign net sellers |
| ABSORPTION | Delta balanced but large lots on buy side |
| NEUTRAL | No clear direction |

**Real example — GGRM Spring bar (May 29, 2026):**
- RX [Asing]: net +11.17B — dominant Bandar, absorbed all sellers
- YU [Asing]: net +4.55B — secondary accumulator
- PD [Lokal]: net −2.06B — local retail distributed to foreign
- GR [Lokal]: net −1.33B — local sold to RX
- Foreign net: +10.16B → **STRONG ACCUMULATION** = Spring confirmed

### Token Setup & Refresh

**The Bearer token expires every 24 hours.** Daily routine:
1. Token server runs automatically (launchd starts it on Mac login)
2. Open Stockbit web in Chrome (any page)
3. Click the **Stockbit Token Sync** Chrome extension icon in toolbar
4. Click **Sync Token to Claude** → token written to `config.json` automatically
5. Done — takes 10 seconds

**If you get 401 errors:** means token expired. Do the 4 steps above.

**Token server management:**
```bash
# Check if running
curl -s http://localhost:3002/health

# Restart manually if needed
launchctl unload ~/Library/LaunchAgents/com.erick.stockbit-token-server.plist
launchctl load  ~/Library/LaunchAgents/com.erick.stockbit-token-server.plist

# View logs
tail -f ~/Library/Logs/stockbit-token-server.log
```

### How Broker Flow Changes Your Entry Decision

| Chart says | Broker flow says | Action |
|------------|-----------------|--------|
| BUY SIGNAL (Spring/SoS/NS) | Foreign net buying (ACCUMULATION) | ✅ Highest conviction — enter |
| BUY SIGNAL | Foreign net selling (DISTRIBUTION) | ⚠️ Skip or reduce size — Bandar distributing |
| BUY SIGNAL | NEUTRAL | Enter, but reduce size vs full position |
| NEUTRAL/WATCH | Foreign net buying strongly | 👀 Add to SC Watch — early accumulation forming |
| SC/EVR below cloud | Foreign net buying | ➕ Confirm SC Watch entry, this is real absorption |

---

## Key Rules to Remember

1. **Never buy below the cloud.** Cloud = the dividing line between bullish and bearish. Exception: Springs can fire below cloud — only need TK > KJ.
2. **Never buy the SoS bar itself.** Wait for LPS — the first NS bar on the pullback 1–3 days later.
3. **Spring is the best entry.** Price is near the base, risk is tight, upside is large.
4. **Never buy after a +20% single-day spike.** That is buying from Bandar, not with them.
5. **Set stop loss in Stockbit immediately** after every entry — not a mental stop.
6. **No signal = no trade.** If nothing is clear, do nothing. Cash is a position.
7. **Boring entries are the best entries.** NS on low volume beats a spike every time.
8. **Check VDA before every entry.** If OBV is declining and VDA shows ND — skip regardless of Wyckoff signal.
9. **Check broker flow before every entry.** If foreign net is distributing on a BUY SIGNAL bar — skip or reduce size. Bandar is exiting, not accumulating.
10. **Exit = turtle trader.** Hold until EXIT SIGNAL fires on dashboard (TK crossunder / Upthrust / high-vol bear weak close). No fixed % target. R:R is dynamic — Ichimoku resistance trails as support.
11. **The screener tells you what to look at. The Analyzer tells you whether to enter. The VDA confirms the volume. Broker flow confirms who is behind the move.**
12. **Analyze after 16:15 WIB.** Daily candles are sealed only after market close. Mid-session analysis is noise.
13. **Just say "morning market check."** Claude reads all screeners, SC Watch, and broker flow automatically. TradingView must be open. Token server must be running.
14. **SC Watch is not a buy list.** Stocks below cloud go on SC Watch. Graduate to buy list only when cloud breakout + 2-Lock confirmed.
15. **Token expires daily.** Open Stockbit in Chrome → click extension → Sync Token. 10 seconds. Do this before each morning scan.

---

---

## Quick Reference — Files & Tools

| What | Where |
|------|-------|
| This workflow guide | `TV-Stock-Analysis/screener_workflow_guide.md` |
| Wyckoff + Ichimoku indicator | `wyckoff_ichimoku_idx_analyzer.pine` → TradingView: "Wyckoff_ichimoku analyzer 1" |
| VDA indicator | `volume_distribution_analyzer.pine` → TradingView: "Volume Distribution Analysis" |
| Stockbit MCP server | `stockbit-mcp/index.js` → registered in `~/.claude.json` as "stockbit" |
| Token server | `stockbit-mcp/token-server.js` → runs via launchd on Mac login |
| Chrome extension | `stockbit-mcp/extension/` → load at `chrome://extensions` (Developer mode) |
| Token config | `stockbit-mcp/config.json` → updated by Chrome extension automatically |
| Trading journal | `trading_journal.md` → SC Watch table at top |
| Investment portfolio | `investment_portfolio_journal.md` |
| US portfolio | `us_portfolio_journal.md` |

*Last updated: 2026-05-31*
