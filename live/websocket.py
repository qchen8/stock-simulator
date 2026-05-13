"""
Real-time WebSocket handler for Alpaca price streams.
Aggregates 1-second trade data into 1m, 5m candles.
"""
import asyncio
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Callable, Dict, List
from alpaca_trade_api.stream import StockStream
import logging

logger = logging.getLogger(__name__)


class Candle:
    """OHLCV candle."""
    def __init__(self, symbol: str, timestamp: datetime, open_price: float):
        self.symbol = symbol
        self.timestamp = timestamp
        self.open = open_price
        self.high = open_price
        self.low = open_price
        self.close = open_price
        self.volume = 0

    def update(self, price: float, size: int):
        """Update candle with new trade."""
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        self.volume += size

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


class CandleAggregator:
    """Aggregate trades into 1m and 5m candles."""
    
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.candles_1m = defaultdict(dict)  # {symbol: {timestamp: Candle}}
        self.candles_5m = defaultdict(dict)
        self.callbacks_1m = []  # (callback(candle), symbol)
        self.callbacks_5m = []
        self.last_timestamp_1m = defaultdict(lambda: None)  # {symbol: timestamp}
        self.last_timestamp_5m = defaultdict(lambda: None)

    def subscribe_1m(self, callback: Callable):
        """Register callback for 1m candle closes."""
        self.callbacks_1m.append(callback)

    def subscribe_5m(self, callback: Callable):
        """Register callback for 5m candle closes."""
        self.callbacks_5m.append(callback)

    def _get_candle_timestamp_1m(self, dt: datetime) -> datetime:
        """Round datetime down to 1m boundary."""
        return dt.replace(second=0, microsecond=0)

    def _get_candle_timestamp_5m(self, dt: datetime) -> datetime:
        """Round datetime down to 5m boundary."""
        minute = (dt.minute // 5) * 5
        return dt.replace(minute=minute, second=0, microsecond=0)

    def update(self, symbol: str, price: float, size: int, timestamp: datetime):
        """Process incoming trade."""
        if symbol not in self.symbols:
            return

        # Update 1m candle
        ts_1m = self._get_candle_timestamp_1m(timestamp)
        if ts_1m not in self.candles_1m[symbol]:
            self.candles_1m[symbol][ts_1m] = Candle(symbol, ts_1m, price)
        self.candles_1m[symbol][ts_1m].update(price, size)

        # Check if 1m candle closed
        if self.last_timestamp_1m[symbol] and ts_1m > self.last_timestamp_1m[symbol]:
            closed_candle = self.candles_1m[symbol][self.last_timestamp_1m[symbol]]
            for callback in self.callbacks_1m:
                callback(closed_candle, "1m")

        self.last_timestamp_1m[symbol] = ts_1m

        # Update 5m candle
        ts_5m = self._get_candle_timestamp_5m(timestamp)
        if ts_5m not in self.candles_5m[symbol]:
            self.candles_5m[symbol][ts_5m] = Candle(symbol, ts_5m, price)
        self.candles_5m[symbol][ts_5m].update(price, size)

        # Check if 5m candle closed
        if self.last_timestamp_5m[symbol] and ts_5m > self.last_timestamp_5m[symbol]:
            closed_candle = self.candles_5m[symbol][self.last_timestamp_5m[symbol]]
            for callback in self.callbacks_5m:
                callback(closed_candle, "5m")

        self.last_timestamp_5m[symbol] = ts_5m

    def get_current_candle_1m(self, symbol: str) -> Candle:
        """Get current (open) 1m candle."""
        now = self._get_candle_timestamp_1m(datetime.utcnow())
        return self.candles_1m[symbol].get(now)

    def get_last_n_candles_1m(self, symbol: str, n: int) -> List[Candle]:
        """Get last N closed 1m candles."""
        candles = sorted(self.candles_1m[symbol].values(), key=lambda c: c.timestamp)
        return candles[-n:] if len(candles) > n else candles

    def get_last_n_candles_5m(self, symbol: str, n: int) -> List[Candle]:
        """Get last N closed 5m candles."""
        candles = sorted(self.candles_5m[symbol].values(), key=lambda c: c.timestamp)
        return candles[-n:] if len(candles) > n else candles


class AlpacaWebSocketHandler:
    """Manage Alpaca WebSocket connection and candle aggregation."""

    def __init__(self, api_key: str, secret_key: str, symbols: List[str]):
        self.api_key = api_key
        self.secret_key = secret_key
        self.symbols = symbols
        self.stream = StockStream(api_key, secret_key)
        self.aggregator = CandleAggregator(symbols)
        self.connected = False

    async def connect(self):
        """Connect to WebSocket and subscribe to symbols."""
        try:
            # Subscribe to quotes for all symbols
            for symbol in self.symbols:
                self.stream.subscribe_quotes(self._on_quote, symbol)
                logger.info(f"Subscribed to {symbol} quotes")

            # Subscribe to trades for candle aggregation
            for symbol in self.symbols:
                self.stream.subscribe_trades(self._on_trade, symbol)
                logger.info(f"Subscribed to {symbol} trades")

            self.connected = True
            logger.info(f"WebSocket connected. Watching {len(self.symbols)} symbols.")

        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.connected = False
            raise

    async def disconnect(self):
        """Disconnect from WebSocket."""
        try:
            await self.stream.close()
            self.connected = False
            logger.info("WebSocket disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")

    def _on_quote(self, quote):
        """Handle quote update (bid/ask/last price)."""
        logger.debug(f"Quote: {quote.symbol} @ {quote.ask_price}")
        # Could trigger alerts here (price targets, extreme moves)

    def _on_trade(self, trade):
        """Handle trade update (aggregate into candles)."""
        self.aggregator.update(
            symbol=trade.symbol,
            price=trade.price,
            size=trade.size,
            timestamp=datetime.fromisoformat(str(trade.timestamp)),
        )

    def subscribe_1m_candles(self, callback: Callable):
        """Register callback for 1m candle closes."""
        self.aggregator.subscribe_1m(callback)

    def subscribe_5m_candles(self, callback: Callable):
        """Register callback for 5m candle closes."""
        self.aggregator.subscribe_5m(callback)

    def get_candles_1m(self, symbol: str, n: int = 50) -> List[Dict]:
        """Get last N 1m candles for a symbol."""
        candles = self.aggregator.get_last_n_candles_1m(symbol, n)
        return [c.to_dict() for c in candles]

    def get_candles_5m(self, symbol: str, n: int = 50) -> List[Dict]:
        """Get last N 5m candles for a symbol."""
        candles = self.aggregator.get_last_n_candles_5m(symbol, n)
        return [c.to_dict() for c in candles]
