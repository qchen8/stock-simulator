# Stock-Simulator: Day Trading Algorithmic Bot Spec

**Version:** 0.2 (Day Trading Edition)  
**Status:** Iterating  
**Last Updated:** 2026-05-12

---

## 1. Overview

An intraday algorithmic trading application focused on **day trading** using **technical analysis** and **real-time price monitoring**. Strategies hold positions 15 minutes to 2 hours max, all closed by end-of-day. Paper-traded on Alpaca with WebSocket streaming.

**Goals:**
- Fast, reactive signal generation from intraday price action
- Multiple concurrent strategies (opening momentum, range scalps, spike fades)
- Real-time WebSocket monitoring for instant entry/exit
- Risk-tight position management (1-2% max loss per trade)
- Safe iterative refinement via backtesting

---

## 2. Core Components

### 2.1 Data Pipeline
- **Real-time Market Data:** WebSocket price streams (1m, 5m candles)
- **Historical Data:** Alpaca REST bars for backtesting
- **News Feed:** Real-time alerts for earnings, Fed decisions, economic releases
- **Technical Indicators:** RSI, MACD, EMA, Bollinger Bands, Volume (all intraday)

### 2.2 Strategy Engine
- **7 Day Trading Strategies:** Each with own entry/exit rules and timeframes
- **Time-Aware:** Market hours (9:30 AM-4:00 PM ET) with strategy rotation
- **Daily Close-out:** All positions liquidated by 3:55 PM ET
- **Real-time Signal Generation:** Triggers on WebSocket candle closes, not batch polling

### 2.3 Execution & Risk Management
- **Quick Fills:** Market orders only (tight bid-ask, liquid day-trading stocks)
- **Micro Position Sizing:** 1-2% risk per trade, auto-scaled by ATR
- **Hard Stops:** Immediate exit on -1 to -2% per trade
- **Daily Cap:** Max 5-10 trades/day, $500 daily loss limit

### 2.4 Monitoring & Alerts
- **Real-time Dashboard:** Active positions, P&L, signal activity
- **Alerts:** Entry/exit signals, stop-loss hits, daily loss threshold
- **Trade Journal:** Every trade logged with reason, entry, exit, P&L

---

## 3. Data Sources & Infrastructure

### Real-time Market Data
- **Alpaca WebSocket API:** Live quote streams, trade streams
- **Candle Assembly:** Local aggregation of trades into 1m, 5m candles
- **Storage:** SQLite for historical backtest data only (live uses streaming)

### News & Catalysts
- **Real-time Alerts:** NewsAPI, earnings calendar, Fed schedule
- **Trigger Filter:** Only process pre-market gaps and major news events

### Technical Indicators (Real-time)
- **Library:** pandas-ta for fast computation
- **Update Frequency:** Recompute on every candle close
- **Lookback:** 50-200 bars in memory (configurable per strategy)

---

## 4. Day Trading Strategies

**Max 5-10 trades/day across all strategies. Rotate through daypart:**

### 4.1 Opening Bell Momentum (9:30-10:30 AM ET)

| Component | Spec |
|-----------|------|
| **Triggers** | Pre-market gap +2% on positive news |
| **Entry** | Buy at open market price, 10 shares (scalable) |
| **Exit** | Profit target +2-3% OR 10:30 AM hard exit |
| **Stop** | -1% hard stop |
| **Hold** | 15-45 minutes |
| **Win Rate** | 60% |
| **Risk/Reward** | 1:2-3 |
| **Ideal Stocks** | TSLA, AAPL, NVDA, MSFT (high volume gappers) |

### 4.2 Bollinger Band Squeeze (Anytime, 5m candles)

| Component | Spec |
|-----------|------|
| **Setup** | BB width < 0.5% of price for 3+ candles |
| **Trigger** | MACD cross + price breaks band |
| **Entry** | Buy/sell at breakout, 5 shares |
| **Exit** | Profit +1-2% OR 2-hour hold max |
| **Stop** | -0.5% |
| **Hold** | 30-90 minutes |
| **Win Rate** | 56-60% |
| **Risk/Reward** | 1:2 |

### 4.3 RSI Extremes (5-15m candles)

| Component | Spec |
|-----------|------|
| **Oversold** | RSI(14) < 20 + price bounces off support |
| **Overbought** | RSI(14) > 80 + price at resistance |
| **Entry** | 10 shares |
| **Exit** | Profit +0.5-1.5% OR 60 min hold max |
| **Stop** | -0.75% |
| **Hold** | 20-60 minutes |
| **Win Rate** | 60-65% (highest quality) |
| **Risk/Reward** | 1:1.5-2 |

### 4.4 Range Scalp (10:30 AM-3:00 PM, 1-5m candles)

| Component | Spec |
|-----------|------|
| **Setup** | Identify 1-hour support/resistance levels |
| **Entry** | Buy support, sell resistance, 5 shares |
| **Exit** | Profit +0.5-1% per scalp |
| **Stop** | -0.75% per trade |
| **Hold** | 10-30 minutes |
| **Frequency** | 5-10 quick scalps (most trades) |
| **Win Rate** | 58-62% |
| **Risk/Reward** | 1:1-1.5 |

### 4.5 EMA Crossover (5-15m candles)

| Component | Spec |
|-----------|------|
| **Setup** | EMA(12) crosses EMA(26) on 5m chart |
| **Volume** | Confirm with volume > 1.5x average |
| **Entry** | 10 shares |
| **Exit** | Profit +1-2% OR EMA cross back |
| **Stop** | -1% |
| **Hold** | 30-90 minutes |
| **Win Rate** | 54-58% |
| **Risk/Reward** | 1:1.5-2 |

### 4.6 Rejection Candle Scalp (5-15m)

| Component | Spec |
|-----------|------|
| **Trigger** | Long wick rejection at support/resistance |
| **Setup** | Candle closes well above/below wick |
| **Entry** | 10 shares at signal |
| **Exit** | Profit +1-1.5% |
| **Stop** | Break of wick low/high |
| **Hold** | 20-45 minutes |
| **Win Rate** | 62-65% (high quality, fewer signals) |
| **Risk/Reward** | 1:1.5 |

### 4.7 News Spike Fade (5m, on catalyst)

| Component | Spec |
|-----------|------|
| **Catalysts** | Earnings, Fed decision, economic data, upgrades |
| **Trigger** | Stock moves 3%+ on headline |
| **Entry** | Fade into dip (long spike down) or short spike (down on bad news) |
| **Exit** | Profit +1-2% from lows |
| **Stop** | -2% (news is volatile) |
| **Hold** | 30-120 minutes |
| **Win Rate** | 55-60% |
| **Risk/Reward** | 1:1.5-2 |

---

## 5. Daily Strategy Rotation

```
9:30 AM ET:    Opening Bell Momentum
  ↓ (9:30-10:30 AM, then stop)

10:30 AM ET:   Range Scalp (primary income strategy, most trades)
  ↓
               EMA Crossover, RSI Extremes, BB Squeeze (supplement as signals appear)
  ↓

2:00 PM ET:    Last 2 hours (exit positions early, don't start new trades)
  ↓

3:55 PM ET:    Liquidate ALL remaining positions (hard rule)
```

**Daily Limits:**
- Max 5-10 trades across all strategies
- Max loss: -$500/day (shutdown after)
- Max hold per trade: 2 hours
- Exit all by 3:55 PM (hard stop, no exceptions)

---

## 6. Architecture

```
stock-simulator/
├── live/
│   ├── websocket.py       # Alpaca WebSocket connection, candle aggregation
│   ├── strategies.py      # All 7 strategies with entry/exit logic
│   ├── signal_engine.py   # Evaluate signals, queue orders
│   ├── execution.py       # Execute orders, track fills
│   └── monitor.py         # Real-time dashboard, alerts
├── backtest/
│   ├── engine.py          # Replay 1m/5m candles, simulate fills
│   ├── optimizer.py       # Parameter search (entry thresholds, etc)
│   └── metrics.py         # Win rate, Sharpe, max loss, equity curve
├── data/
│   ├── fetcher.py         # Alpaca REST for historical bars
│   ├── indicators.py      # Fast RSI, MACD, EMA, BB computation
│   └── cache.py           # In-memory bar storage (current day)
├── config/
│   ├── strategies.json    # Entry/exit thresholds per strategy
│   ├── symbols.json       # Watchlist (TSLA, AAPL, NVDA, etc)
│   └── risk.json          # Position size, daily loss cap, hours
├── tests/
│   ├── test_strategies.py
│   ├── test_backtest.py
│   └── test_execution.py
├── main.py                # Entry: backtest or live mode
├── SPEC.md                # This file
└── requirements.txt
```

---

## 7. Tech Stack

| Component | Library | Notes |
|-----------|---------|-------|
| **Broker** | alpaca-trade-api + websockets | Paper + live |
| **WebSocket** | websockets (Python 3.9+) | Real-time candles |
| **Analysis** | pandas, numpy, pandas-ta | Fast computation |
| **Indicators** | pandas-ta | RSI, MACD, EMA, BB, Volume |
| **Database** | SQLite | Backtest historical bars only |
| **Scheduling** | APScheduler | Market hours, daily close-out |
| **Backtest** | Custom engine | Walk-forward simulation on 1m/5m bars |
| **Logging** | Python logging + CSV trade journal | Full audit trail |
| **Config** | JSON | Strategy params, symbols, risk |

---

## 8. Configuration Example

```json
{
  "mode": "live",
  "symbols": ["TSLA", "AAPL", "NVDA", "MSFT", "AMD"],
  "market_hours": {
    "open": "09:30",
    "close": "16:00",
    "last_entry": "15:00"
  },
  "risk": {
    "max_trades_per_day": 10,
    "max_daily_loss": 500,
    "risk_per_trade": 0.02,
    "max_position_hold_minutes": 120,
    "close_all_at": "15:55"
  },
  "strategies": {
    "opening_bell_momentum": {
      "enabled": true,
      "hours": "09:30-10:30",
      "position_size": 10,
      "profit_target": 2.5,
      "stop_loss": 1.0
    },
    "range_scalp": {
      "enabled": true,
      "hours": "10:30-15:00",
      "position_size": 5,
      "profit_target": 0.75,
      "stop_loss": 0.75,
      "candle_size": "5m"
    },
    "rsi_extremes": {
      "enabled": true,
      "rsi_period": 14,
      "oversold": 20,
      "overbought": 80,
      "position_size": 10,
      "profit_target": 1.0,
      "stop_loss": 0.75
    },
    "ema_crossover": {
      "enabled": true,
      "fast_ema": 12,
      "slow_ema": 26,
      "position_size": 10,
      "profit_target": 1.5,
      "stop_loss": 1.0,
      "volume_multiplier": 1.5
    },
    "bb_squeeze": {
      "enabled": true,
      "bb_width_threshold": 0.5,
      "position_size": 5,
      "profit_target": 1.5,
      "stop_loss": 0.5
    },
    "rejection_candle": {
      "enabled": true,
      "position_size": 10,
      "profit_target": 1.25,
      "stop_loss": 1.0
    },
    "news_spike_fade": {
      "enabled": true,
      "min_move_percent": 3.0,
      "position_size": 10,
      "profit_target": 1.5,
      "stop_loss": 2.0
    }
  }
}
```

---

## 9. Workflow

### Backtest Mode
1. Download 1m + 5m bars for symbol(s) (3-6 months historical)
2. Simulate opening bell momentum, range scalps, all strategies
3. For each bar:
   - Compute indicators (RSI, MACD, EMA, BB)
   - Evaluate all strategy signals
   - Queue orders if triggered
   - Execute at bar close price (assume instant fill)
   - Track P&L, win/loss, hold time
4. Generate report: win rate, Sharpe, max loss, equity curve

### Live Mode
1. On startup (8:00 AM): Fetch current positions, account state
2. Connect to Alpaca WebSocket, subscribe to price streams
3. On every 1m candle close:
   - Compute indicators
   - Evaluate all strategy signals
   - Place orders if triggered
   - Monitor for stop-loss hits
   - Log all activity
4. At 2:00 PM: Stop entering new trades
5. At 3:55 PM: Liquidate all remaining positions (hard exit)
6. Post-market: Generate daily summary, P&L, trade journal

---

## 10. Development Phases

### Phase 1: Foundation (Week 1)
- [ ] WebSocket connection + real-time 1m/5m candle aggregation
- [ ] Indicator calculations (RSI, MACD, EMA, BB, Volume)
- [ ] Backtest engine (1m/5m replay, order simulation)
- [ ] Single strategy implementation (Range Scalp, simplest)
- [ ] Paper trade on 1 symbol (TSLA)

### Phase 2: Strategies (Week 2)
- [ ] Implement all 7 strategies
- [ ] Configurable entry/exit thresholds (JSON)
- [ ] Strategy rotation + time-aware scheduling
- [ ] Daily close-out logic (3:55 PM liquidation)
- [ ] Backtest all strategies on 3-month data

### Phase 3: Risk & Execution (Week 3)
- [ ] Position sizing (ATR-scaled, % risk)
- [ ] Hard stop-loss enforcement
- [ ] Daily loss cap ($500)
- [ ] Trade journal (CSV: time, symbol, entry, exit, P&L, reason)
- [ ] Alerts (Slack/Discord/Email on major events)

### Phase 4: Live Trading & Refinement (Week 4+)
- [ ] Deploy to paper account (real-time)
- [ ] Parameter optimization (backtest → live validation)
- [ ] Multi-symbol support (5-10 watch list)
- [ ] Performance dashboard (equity curve, daily P&L)
- [ ] Live → Production migration path

---

## 11. Known Unknowns & Decisions

1. **WebSocket vs Polling:** Use Alpaca WebSocket (yes) or REST polling every 1m (slower)?
   - *Decision:* WebSocket for real-time signals, polling is too slow for day trading.

2. **Position Sizing:** Fixed shares (10, 5) or percent-of-capital? ATR-scaled?
   - *Decision:* Start with fixed shares, scale by ATR volatility later.

3. **Entry Timing:** Enter on candle close or mid-candle on signal?
   - *Decision:* Candle close only (prevents whipsaws, cleaner backtest).

4. **Fill Assumption:** Instant at close price or add slippage?
   - *Decision:* Assume instant (liquid day-trade stocks), add 1-cent buffer for live.

5. **Strategy Conflicts:** What if 2 strategies signal same symbol same time?
   - *Decision:* Combine into single larger position, exit on first signal triggered.

6. **News Alerts Integration:** Real-time earnings/Fed/econ calendar?
   - *Decision:* NewsAPI for now, add calendar alerts in Phase 4.

---

## 12. Success Metrics

- **Backtest (3-month):** >55% win rate, Sharpe >1.0, max loss <20%, avg trade +0.5-1.5%
- **Paper Trading (4+ weeks):** Consistent daily P&L, >60% of backtest results, no catastrophic losses
- **Code:** 80%+ test coverage, <10 second signal latency, zero crashes
- **Operational:** Max 10 trades/day, zero positions after 3:55 PM, 100% logged

---

## 13. Next Steps

1. **Review & iterate spec** — finalize strategies, config, risk model
2. **Lock architecture** (WebSocket real-time vs REST polling decision)
3. **Start Phase 1** — WebSocket + 1m candles + basic backtest engine
4. **Weekly demos** — show backtest results, iterate on thresholds

---

_Ready to build? Let's validate the spec with some backtest data first._
