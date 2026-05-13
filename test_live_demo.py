"""
Live demo: Generate trades and stream to dashboard.
Shows the complete architecture in action.
"""
import asyncio
import json
import logging
import time
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).parent))

from backtest.engine import BacktestEngine, MockDataGenerator, BacktestBar
from live.events import EventBus, EventType, Event
from live.dashboard import DashboardServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SimpleScalpStrategy:
    """Generate trades for demo."""

    def __init__(self, engine: BacktestEngine, event_bus: EventBus):
        self.engine = engine
        self.event_bus = event_bus
        self.bars_seen = 0
        self.in_position = False

    def evaluate(self, bar: BacktestBar):
        """Simple oscillating strategy for demo."""
        self.bars_seen += 1

        # Skip first 10 bars
        if self.bars_seen < 10:
            return

        # Simple: buy on odd bars, sell on even bars (for demo)
        if self.bars_seen % 8 == 0 and not self.in_position:
            # Buy signal
            self.event_bus.signal_generated(
                symbol=bar.symbol,
                strategy="demo_scalp",
                signal="buy",
                score=0.72,
                candle_time=bar.timestamp.isoformat(),
            )

            self.engine.open_position(
                symbol=bar.symbol,
                qty=10,
                entry_price=bar.close,
                timestamp=bar.timestamp,
                strategy="demo_scalp",
            )
            self.in_position = True

        elif self.bars_seen % 8 == 4 and self.in_position:
            # Sell signal
            self.event_bus.signal_generated(
                symbol=bar.symbol,
                strategy="demo_scalp",
                signal="sell",
                score=0.55,
                candle_time=bar.timestamp.isoformat(),
            )

            # Close position
            if bar.symbol in self.engine.positions:
                self.engine._close_position(
                    bar.symbol,
                    bar.close,
                    bar.timestamp,
                    "signal_exit",
                )
            self.in_position = False


def run_live_demo():
    """Run demo with trades streaming to dashboard."""
    logger.info("=" * 70)
    logger.info("🚀 Stock Simulator - Live Demo")
    logger.info("=" * 70)

    # Setup
    Path("logs").mkdir(exist_ok=True)
    events = EventBus(log_file="logs/events.jsonl")
    dashboard = DashboardServer(events, port=5000)

    # Start dashboard in background
    dashboard.run_async()
    time.sleep(1)
    logger.info("📊 Dashboard: http://127.0.0.1:5000")
    logger.info("🌐 Open browser now! Events will stream in real-time.\n")

    # Generate data
    logger.info("📈 Generating mock market data (200 bars)...")
    bars = MockDataGenerator.generate_range_bound(
        symbol="TSLA",
        start_price=250.0,
        num_bars=200,
        volatility=0.008,
    )
    logger.info(f"✅ Generated {len(bars)} bars\n")

    # Create engine
    engine = BacktestEngine(symbol="TSLA", bars=bars, event_bus=events)

    # Create strategy
    strategy = SimpleScalpStrategy(engine, events)
    engine.subscribe(strategy.evaluate)

    # Market open
    events.publish(Event(
        type=EventType.MARKET_OPEN,
        timestamp=datetime.utcnow(),
        data={"symbol": "TSLA", "time": "09:30"},
    ))

    # Run backtest
    logger.info("▶️  Starting backtest...\n")
    time.sleep(1)
    report = engine.run()

    # Market close
    events.publish(Event(
        type=EventType.MARKET_CLOSE,
        timestamp=datetime.utcnow(),
        data={"daily_pnl": engine.daily_pnl, "trades": len(engine.closed_trades)},
    ))

    # Report
    logger.info("\n" + "=" * 70)
    logger.info("✅ Backtest Complete!")
    logger.info("=" * 70)
    logger.info(f"\nSymbol: {report['symbol']}")
    logger.info(f"Trades: {report.get('trades', 0)}")
    if report.get('trades', 0) > 0:
        logger.info(f"Wins: {report.get('wins', 0)} | Losses: {report.get('losses', 0)}")
        logger.info(f"Win Rate: {report.get('win_rate_pct', 0):.1f}%")
        logger.info(f"Total P&L: ${report.get('total_pnl', 0):.2f}")
        logger.info(f"Return: {report.get('return_pct', 0):.2f}%")

    logger.info(f"\n📋 Event log: logs/events.jsonl")
    logger.info(f"🔗 Dashboard: http://127.0.0.1:5000\n")

    # Keep server running
    logger.info("⏳ Server will run for 45 seconds...")
    logger.info("💡 Try these in the browser:\n")
    logger.info("  • Refresh page to see live updates")
    logger.info("  • Watch the event log populate in real-time")
    logger.info("  • See trades appear in the table\n")

    try:
        for i in range(45):
            time.sleep(1)
            print(".", end="", flush=True)
            if i == 20:
                print()  # New line every 20 dots
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Shutdown requested")

    logger.info("\n✅ Demo complete!")


if __name__ == "__main__":
    run_live_demo()
