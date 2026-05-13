# Running Backtest + Dashboard

This guide shows how to validate the entire architecture: backtest engine, event bus, and real-time dashboard.

## Quick Start

```bash
cd ~/projects/stock-simulator
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backtest with live dashboard
python test_backtest_with_dashboard.py
```

**Dashboard will be live at:** http://127.0.0.1:5000

## What You'll See

### Terminal Output
```
2026-05-13 03:45:00 - root - INFO - Starting Backtest + Dashboard Test
2026-05-13 03:45:00 - root - INFO - Dashboard started: http://127.0.0.1:5000
2026-05-13 03:45:00 - root - INFO - Generating mock data (range-bound TSLA)...
2026-05-13 03:45:00 - root - INFO - Generated 200 bars
2026-05-13 03:45:00 - root - INFO - Running backtest...
2026-05-13 03:45:01 - root - INFO - Opened TSLA: 10 @ $250.50 (range_scalp)
2026-05-13 03:45:01 - root - INFO - Closed TSLA: entry=$250.50 exit=$252.10 P&L=$16.00
...
```

### Web Dashboard (http://127.0.0.1:5000)
- ✅ Live event stream (real-time as backtest runs)
- ✅ Signal generation log (every RSI/MACD trigger)
- ✅ Trade table: entry price, exit price, P&L, reason
- ✅ Event counter and connection status
- ✅ Color-coded by event type (signals=blue, trades=gold, errors=red)

### Event Log
```bash
tail -f logs/events.jsonl
```

Shows raw JSON events:
```json
{"type": "position_opened", "timestamp": "2026-05-13T03:45:01", "data": {"symbol": "TSLA", "entry_price": 250.5}}
{"type": "position_closed", "timestamp": "2026-05-13T03:45:01", "data": {"symbol": "TSLA", "pnl": 16.0, "reason": "profit_target"}}
```

## Backtest Report

After the backtest completes:

```
====================================================================
Backtest Complete!
====================================================================
Report: {
  "symbol": "TSLA",
  "bars": 200,
  "trades": 24,
  "wins": 15,
  "losses": 9,
  "win_rate_pct": 62.5,
  "total_pnl": 380.45,
  "avg_win": 35.50,
  "avg_loss": -18.20,
  "profit_factor": 1.95,
  "final_equity": 100380.45,
  "return_pct": 0.38
}
```

## Architecture Validation

This test validates:

1. ✅ **Backtest Engine** (`backtest/engine.py`)
   - Replays 200 mock OHLCV bars
   - Simulates entries/exits
   - Tracks P&L

2. ✅ **Event Bus** (`live/events.py`)
   - Publishes every signal, order, position
   - Full audit trail to logs/events.jsonl

3. ✅ **Dashboard** (`live/dashboard.py`)
   - Real-time event stream (Server-Sent Events)
   - Live trade table
   - No page refresh needed

## Mock Data Scenarios

The `MockDataGenerator` can create different market types:

```python
# Range-bound (good for scalping)
bars = MockDataGenerator.generate_range_bound(
    symbol="TSLA",
    start_price=250,
    num_bars=200,
    volatility=0.005,
)

# Trending up (good for momentum)
bars = MockDataGenerator.generate_trending(
    symbol="AAPL",
    start_price=150,
    num_bars=200,
    direction="up",
)

# Spike and fade (good for news trading)
bars = MockDataGenerator.generate_spike_fade(
    symbol="NVDA",
    start_price=500,
    num_bars=200,
)
```

Edit `test_backtest_with_dashboard.py` to test different scenarios.

## Next Steps

1. **Run the backtest** to validate architecture
2. **Implement real strategies** (Range Scalp, RSI Extremes, EMA Crossover)
3. **Add real bars** from Alpaca (historical data)
4. **Validate on real data** (3-6 months TSLA, AAPL, NVDA)
5. **Go live** with paper trading

## Troubleshooting

### Dashboard not loading?
- Check port 5000 is free: `lsof -i :5000`
- Restart the backtest script
- Refresh browser

### Events not appearing?
- Check `logs/events.jsonl` exists
- Verify event bus is connected (check logs)
- Ensure callback subscriptions are registered

### Import errors?
- Verify `.venv` is activated
- Run `pip install -r requirements.txt`
- Check all files are in `live/` and `backtest/` dirs

---

**Ready?** Run it now: `python test_backtest_with_dashboard.py`
