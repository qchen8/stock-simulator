"""
Main entry point for live trading with real-time WebSocket monitoring.
Starts WebSocket handler, event bus, and web dashboard.
"""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY

from websocket import AlpacaWebSocketHandler
from events import EventBus, EventType
from dashboard import DashboardServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class LiveTradingBot:
    """Main bot that integrates WebSocket, signals, and execution."""

    def __init__(self, config_path: str = "config/strategies.json"):
        # Load config
        with open(config_path) as f:
            self.config = json.load(f)

        # Setup event system
        self.events = EventBus(log_file="logs/events.jsonl")

        # Setup WebSocket
        self.websocket = AlpacaWebSocketHandler(
            api_key=ALPACA_API_KEY,
            secret_key=ALPACA_SECRET_KEY,
            symbols=self.config.get("symbols", ["TSLA", "AAPL", "NVDA"]),
        )

        # Setup dashboard
        self.dashboard = DashboardServer(self.events)

        # Trading state
        self.positions = {}  # {symbol: {qty, entry_price, strategy}}
        self.daily_pnl = 0.0
        self.trades_today = 0

    async def run(self):
        """Start live trading."""
        logger.info("=" * 60)
        logger.info("Starting Live Trading Bot")
        logger.info("=" * 60)

        # Start dashboard
        self.dashboard.run_async()
        logger.info(f"Dashboard: http://127.0.0.1:5000")

        # Connect WebSocket
        try:
            await self.websocket.connect()
        except Exception as e:
            self.events.error(f"Failed to connect WebSocket: {e}")
            return

        # Subscribe to candle closes
        self.websocket.subscribe_1m_candles(self._on_candle_1m)
        self.websocket.subscribe_5m_candles(self._on_candle_5m)

        # Market hours loop
        await self._market_hours_loop()

    async def _market_hours_loop(self):
        """Main market hours loop."""
        logger.info("Market hours loop started")
        try:
            while True:
                await asyncio.sleep(1)
                now = datetime.utcnow().time()

                # Check market hours (9:30 AM - 4:00 PM ET)
                market_open = datetime.min.time()
                market_open = market_open.replace(hour=14, minute=30)  # 9:30 AM ET
                market_close = datetime.min.time()
                market_close = market_close.replace(hour=20, minute=0)  # 4:00 PM ET

                if now < market_open or now > market_close:
                    if now > market_close:
                        # After hours: liquidate all positions
                        await self._close_all_positions()
                    continue

                # During market hours: check for signals
                # (actual signal logic would go here)

        except Exception as e:
            logger.error(f"Error in market loop: {e}")
            self.events.error(f"Market loop error: {e}")

    async def _close_all_positions(self):
        """Liquidate all positions at end of day."""
        if not self.positions:
            return

        logger.info("Closing all positions at end of day")
        for symbol, pos in self.positions.items():
            # TODO: Place closing order via Alpaca API
            pass
        self.positions.clear()

    def _on_candle_1m(self, candle, timeframe: str):
        """Process 1m candle close (for fast strategies)."""
        # Log candle
        logger.debug(f"1m Candle: {candle.symbol} {candle.close}")

        # TODO: Evaluate Range Scalp, RSI Extremes here
        # Example:
        # signal = self.range_scalp_strategy.evaluate(candle)
        # if signal:
        #     self.events.signal_generated(...)
        #     self.place_order(...)

    def _on_candle_5m(self, candle, timeframe: str):
        """Process 5m candle close (for medium strategies)."""
        # Log candle
        logger.debug(f"5m Candle: {candle.symbol} {candle.close}")

        # TODO: Evaluate EMA Crossover, BB Squeeze here

    async def place_order(self, symbol: str, side: str, qty: int, strategy: str):
        """Place an order and publish event."""
        self.events.order_placed(symbol=symbol, side=side, qty=qty, order_type="market")

        # TODO: Place actual order via Alpaca API
        # order = alpaca_api.submit_order(symbol, qty, side, "market")

        self.events.order_filled(
            order_id="mock_order_id",
            symbol=symbol,
            side=side,
            qty=qty,
            fill_price=100.0,  # Mock
        )

        # Update position
        self.positions[symbol] = {"qty": qty, "entry_price": 100.0, "strategy": strategy}
        self.events.position_opened(
            symbol=symbol, side=side, qty=qty, entry_price=100.0, strategy=strategy
        )


async def main():
    """Entry point."""
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)

    # Initialize bot
    bot = LiveTradingBot()

    # Run
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
