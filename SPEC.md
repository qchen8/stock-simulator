# Stock-Simulator: Algorithmic Trading App Spec

**Version:** 0.1 (Draft)  
**Status:** Iterating  
**Last Updated:** 2026-05-12

---

## 1. Overview

An algorithmic trading application that combines **technical chart analysis** and **news sentiment** to generate buy/sell signals. Paper-traded on Alpaca to validate strategies before live deployment.

**Goals:**
- Automated signal generation from multiple data sources
- Backtestable strategies
- Real-time trade execution (paper trading first)
- Performance tracking and metrics
- Safe, iterative strategy refinement

---

## 2. Core Components

### 2.1 Data Pipeline
- **Market Data:** Historical and real-time bars (OHLCV) from Alpaca
- **News Feed:** Headlines, sentiment scores (TextBlob or transformers)
- **Technical Indicators:** RSI, MACD, Bollinger Bands, SMA/EMA, ATR, Stochastic
- **Reference Data:** Assets, trading hours, market calendar

### 2.2 Signal Generation
- **Technical Signals:** Indicator-based rules (e.g., RSI < 30 = oversold, MA crossover)
- **Sentiment Signals:** News score aggregation (bullish vs bearish headlines)
- **Combined Signal:** Weighted merge of tech + sentiment into buy/hold/sell recommendations
- **Filtering:** Risk checks (position sizing, max loss, correlation)

### 2.3 Strategy Engine
- **Rule-based:** Condition → Action (if RSI < 30 AND sentiment > 0.6, buy)
- **Backtestable:** Replay historical data, measure returns/drawdown
- **Live Mode:** Real-time updates, execute orders via Alpaca
- **Configurable:** Thresholds, weights, symbols, timeframes

### 2.4 Execution & Risk Management
- **Order Placement:** Market, limit, stop-loss orders
- **Position Sizing:** Kelly fraction or fixed % of portfolio
- **Portfolio Limits:** Max 5 positions, max loss per trade, daily stop-loss
- **Logging:** All orders, signals, P&L tracked

### 2.5 Monitoring & Reporting
- **Dashboard:** Real-time positions, P&L, signal activity
- **Metrics:** Win rate, Sharpe ratio, max drawdown, monthly returns
- **Alerts:** Major position changes, risk threshold breaches

---

## 3. Data Sources

### Market Data
- **Alpaca Trading API:** Bars (1m, 5m, 15m, 1h, 1d), snapshots, quotes
- **Storage:** In-memory cache + SQLite for historical backtest data

### News Sentiment
- **Primary:** NewsAPI (headlines, filtering by ticker)
- **Fallback:** Alpha Vantage (news from earnings/events)
- **Sentiment:** TextBlob (simple) or HuggingFace transformers (more accurate)

### Technical Indicators
- **Library:** pandas-ta (or ta-lib if available)
- **Computed on:** Real-time bars, recomputed as new candles close

---

## 4. Trading Signals & Logic

### 4.1 Technical Signals (Examples)

| Signal | Rules | Confidence |
|--------|-------|------------|
| **RSI Oversold** | RSI(14) < 30 | Low (noisy alone) |
| **MA Golden Cross** | SMA(50) > SMA(200) | Medium |
| **MACD Bullish** | MACD > Signal line, histogram > 0 | Medium |
| **Bollinger Pop** | Price closes above upper BB | Low |
| **Trend Confirmation** | Close > SMA(20) for 3 candles | Medium |

### 4.2 Sentiment Signals (Examples)

| Signal | Rules | Confidence |
|--------|-------|------------|
| **Positive News** | Sentiment score > 0.6, volume > 5 | Medium |
| **Negative Catalyst** | Sentiment < -0.5, recent (< 24h) | Medium |
| **Consensus Shift** | 70% positive headlines last 7d | High |

### 4.3 Combined Logic

```
BUY if:
  (Technical Score > 0.6) AND (Sentiment > 0.3) AND (Not in position)
  
SELL if:
  (Position underwater > 5%) OR (Technical Score < 0.3) OR (Sentiment < -0.5)
  
HOLD otherwise
```

**Scoring:** Simple weighted average
- Technical: 60%
- Sentiment: 40%
- Final Score: 0–1 (0=sell, 0.5=neutral, 1=buy)

---

## 5. Architecture

```
stock-simulator/
├── data/
│   ├── fetcher.py          # Alpaca bars, NewsAPI headlines
│   ├── indicators.py        # Technical analysis calculations
│   ├── sentiment.py         # News sentiment scoring
│   └── storage.py          # SQLite for historical data
├── signals/
│   ├── technical.py        # RSI, MACD, BB rules
│   ├── sentiment.py        # News score aggregation
│   └── combined.py         # Merge tech + sentiment into action
├── strategies/
│   ├── base.py             # Strategy template/interface
│   ├── rsi_ma_combo.py     # Example: RSI + MA + sentiment
│   └── config.json         # Strategy parameters (thresholds, weights)
├── execution/
│   ├── trader.py           # Place/cancel orders via Alpaca
│   └── risk.py             # Position sizing, max loss checks
├── backtest/
│   ├── engine.py           # Replay historical bars
│   └── metrics.py          # Sharpe, drawdown, win rate
├── live/
│   ├── scheduler.py        # APScheduler for periodic checks
│   └── monitor.py          # Dashboard/alerts
├── tests/
│   ├── test_signals.py
│   ├── test_backtester.py
│   └── test_trader.py
├── main.py                 # Entry point (backtest or live)
├── SPEC.md                 # This file
├── README.md
└── requirements.txt
```

---

## 6. Tech Stack

| Component | Library | Notes |
|-----------|---------|-------|
| **Trading API** | alpaca-trade-api | Paper + live |
| **Data Fetching** | requests | NewsAPI, Alpaca REST |
| **Analysis** | pandas, numpy | Data manipulation |
| **Indicators** | pandas-ta | Technical analysis |
| **Sentiment** | TextBlob or transformers | News scoring |
| **Database** | SQLite | Historical bars for backtest |
| **Scheduling** | APScheduler | Periodic signal checks |
| **Backtesting** | Custom engine | Walk-forward simulation |
| **Config** | JSON/YAML | Strategy parameters |
| **Testing** | pytest | Unit + integration tests |

---

## 7. Configuration Example

```json
{
  "strategy": "rsi_ma_combo",
  "symbols": ["AAPL", "TSLA", "NVDA"],
  "timeframe": "1h",
  "position_size": 0.1,
  "max_positions": 5,
  "max_loss_per_trade": 100,
  "max_daily_loss": 500,
  "technical": {
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "ma_fast": 20,
    "ma_slow": 50,
    "ma_confirmation_bars": 3
  },
  "sentiment": {
    "enabled": true,
    "min_confidence": 0.6,
    "weight": 0.4,
    "news_lookback_days": 7
  },
  "combined": {
    "buy_threshold": 0.6,
    "sell_threshold": 0.3
  }
}
```

---

## 8. Workflow

### Backtest Mode
1. Load historical bars for symbol(s) and date range
2. For each candle:
   - Compute technical indicators
   - Fetch news sentiment for the day
   - Calculate combined signal
   - Simulate order execution at candle close price
   - Track P&L, metrics
3. Generate report (Sharpe, drawdown, win rate, equity curve)

### Live Mode
1. On startup, fetch current positions, account state
2. Every N minutes (configurable):
   - Fetch latest bars and news
   - Compute signals
   - Execute trades if signal triggers
   - Log all activity
3. Monitor and alert on breaches

---

## 9. Development Phases

### Phase 1: Foundation (Week 1)
- [ ] Data fetcher (Alpaca bars, NewsAPI)
- [ ] Technical indicator calculations
- [ ] Sentiment scoring (TextBlob baseline)
- [ ] Combined signal engine
- [ ] Paper trade execution (single symbol)

### Phase 2: Strategy & Backtest (Week 2)
- [ ] Configurable strategy framework
- [ ] Backtester engine
- [ ] Performance metrics (Sharpe, drawdown, etc.)
- [ ] Validate on 6-month historical data

### Phase 3: Safety & Monitoring (Week 3)
- [ ] Risk management (position limits, max loss)
- [ ] Real-time scheduler
- [ ] Alert system (email, Slack, Discord)
- [ ] Live monitoring dashboard

### Phase 4: Refinement (Week 4+)
- [ ] Multi-symbol support
- [ ] Parameter optimization
- [ ] Advanced strategies (pairs trading, ML features)
- [ ] Logging/audit trail

---

## 10. Known Unknowns & Questions

1. **Sentiment Accuracy:** How often should we update news? Daily? Intraday? Will simple TextBlob suffice or do we need transformers?
2. **Signal Weighting:** Is 60/40 tech/sentiment right, or should it be dynamic per symbol?
3. **Timeframe:** Start with 1h candles? Or 1d for lower churn?
4. **Position Sizing:** Kelly fraction, fixed %, or dynamic based on volatility?
5. **News Source:** NewsAPI only, or supplement with Twitter, earnings calendars, SEC filings?
6. **Drawdown Limits:** Daily stop-loss at -$500? Per-trade at -$100? Adjustable by symbol?
7. **Backtester Slippage:** Assume instant fill at candle close, or add slippage buffer?

---

## 11. Success Metrics

- **Backtest:** Sharpe ratio > 1.0, max drawdown < 20%, win rate > 55%
- **Paper Trading:** Consistent profitability over 4+ weeks
- **Code Quality:** 80%+ test coverage, clear logging
- **UX:** Easy to modify strategy params without code changes

---

## Next Steps

1. **Review & iterate** on this spec — adjust signal logic, tech stack, phases
2. **Lock architecture** once aligned
3. **Start Phase 1** — basic data pipeline and single-symbol backtest
4. **Weekly checkpoints** to measure progress and pivot if needed

---

_Feedback? Edge cases? Let's refine before building._
