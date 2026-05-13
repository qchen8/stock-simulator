"""
Test script: Run backtest with mock data and visualize on dashboard.
Validates the entire architecture (engine + events + UI).
"""
import asyncio
import json
import logging
import time
from pathlib import Path
from datetime import datetime

# Add current dir to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from backtest.engine import BacktestEngine, MockDataGenerator
from live.events import EventBus, EventType, Event
from live.dashboard import DashboardServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SimpleRangeScalpStrategy:
    """Simple range scalp strategy for testing."""

    def __init__(self, engine: BacktestEngine, event_bus: EventBus):
        self.engine = engine
        self.event_bus = event_bus
        self.bars_seen = 0
        self.support = None
        self.resistance = None
        self.lookback = 20

    def evaluate(self, bar):
        """Evaluate bar for range scalp signals."""
        self.bars_seen += 1

        # Wait for enough bars
        if self.bars_seen < self.lookback:
            return

        # Calculate support/resistance (simple min/max)
        if self.support is None or self.resistance is None:
            self._update_levels()

        # Buy at support
        if bar.close <= self.support * 1.001 and "BUY" not in self.engine.positions:
            self.event_bus.signal_generated(
                symbol=bar.symbol,
                strategy="range_scalp",
                signal="buy",
                score=0.75,
                candle_time=bar.timestamp.isoformat(),
            )
            self.engine.open_position(
                symbol=bar.symbol,
                qty=10,
                entry_price=bar.close,
                timestamp=bar.timestamp,
                strategy="range_scalp",
            )

        # Sell at resistance (already handled by engine exit logic)

    def _update_levels(self):
        """Update support/resistance levels."""
        # Dummy: just use current close
        self.support = 100.0
        self.resistance = 105.0


def test_backtest():
    """Run backtest with mock data and dashboard."""
    logger.info("=" * 60)
    logger.info("Starting Backtest + Dashboard Test")
    logger.info("=" * 60)

    # Create logs directory
    Path("logs").mkdir(exist_ok=True)

    # Setup event bus
    events = EventBus(log_file="logs/events.jsonl")

    # Setup dashboard
    dashboard = DashboardServer(events, port=5000)
    dashboard.run_async()
    logger.info("Dashboard started: http://127.0.0.1:5000")
    logger.info("Open in browser to see live backtest events!")
    time.sleep(1)  # Give dashboard time to start

    # Generate mock data
    logger.info("Generating mock data (range-bound TSLA)...")
    bars = MockDataGenerator.generate_range_bound(
        symbol="TSLA",
        start_price=250.0,
        num_bars=200,
        volatility=0.005,
    )
    logger.info(f"Generated {len(bars)} bars")

    # Create backtest engine
    engine = BacktestEngine(symbol="TSLA", bars=bars, event_bus=events)

    # Create strategy
    strategy = SimpleRangeScalpStrategy(engine, events)
    engine.subscribe(strategy.evaluate)

    # Publish market open event
    events.publish(
        Event(
            type=EventType.MARKET_OPEN,
            timestamp=datetime.utcnow(),
            data={"symbol": "TSLA", "time": "09:30"},
        )
    )

    # Run backtest
    logger.info("Running backtest...")
    report = engine.run()

    # Publish market close event
    events.publish(
        Event(
            type=EventType.MARKET_CLOSE,
            timestamp=datetime.utcnow(),
            data={"daily_pnl": engine.daily_pnl},
        )
    )

    logger.info("=" * 60)
    logger.info("Backtest Complete!")
    logger.info("=" * 60)
    logger.info(f"Report: {json.dumps(report, indent=2)}")
    logger.info(f"\nDashboard: http://127.0.0.1:5000")
    logger.info(f"Event log: logs/events.jsonl")
    logger.info("\nRefresh browser to see live updates!")

    # Keep running for 30 seconds so user can view dashboard
    logger.info("\nServer running for 30 seconds... (Ctrl+C to exit)")
    try:
        for i in range(30):
            time.sleep(1)
            print(".", end="", flush=True)
    except KeyboardInterrupt:
        logger.info("\nShutdown requested")

    return report


def test_multiple_scenarios():
    """Run multiple backtest scenarios."""
    logger.info("Running multiple scenario tests...")

    scenarios = [
        ("TSLA Range-Bound", "range_bound", {"volatility": 0.005, "trend": 0.0}),
        ("NVDA Uptrend", "trending", {"direction": "up"}),
        ("AAPL Downtrend", "trending", {"direction": "down"}),
        ("MSFT Spike-Fade", "spike_fade", {}),
    ]

    results = []

    for name, data_type, kwargs in scenarios:
        logger.info(f"\nScenario: {name}")

        if data_type == "range_bound":
            bars = MockDataGenerator.generate_range_bound("TEST", 100, 200, **kwargs)
        elif data_type == "trending":
            bars = MockDataGenerator.generate_trending("TEST", 100, 200, **kwargs)
        elif data_type == "spike_fade":
            bars = MockDataGenerator.generate_spike_fade("TEST", 100, 200, **kwargs)

        events = EventBus()
        engine = BacktestEngine("TEST", bars, event_bus=events)
        strategy = SimpleRangeScalpStrategy(engine, events)
        engine.subscribe(strategy.evaluate)

        report = engine.run()
        report["scenario"] = name
        results.append(report)

    logger.info("\n" + "=" * 60)
    logger.info("Summary of All Scenarios:")
    logger.info("=" * 60)
    for r in results:
        logger.info(
            f"{r['scenario']:20} | Trades: {r.get('trades', 0):3d} | "
            f"Win Rate: {r.get('win_rate_pct', 0):5.1f}% | "
            f"P&L: ${r.get('total_pnl', 0):8.2f}"
        )


if __name__ == "__main__":
    test_backtest()
    # Uncomment to test multiple scenarios:
    # test_multiple_scenarios()
