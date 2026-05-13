"""
Backtest engine: replay historical bars and simulate trades.
Validates strategies against historical data before live trading.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Callable
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


class BacktestBar:
    """Simulated OHLCV bar for backtesting."""

    def __init__(self, symbol: str, timestamp: datetime, open_: float, high: float, low: float, close: float, volume: int):
        self.symbol = symbol
        self.timestamp = timestamp
        self.open = open_
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

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


class BacktestEngine:
    """Replay historical bars and simulate strategy execution."""

    def __init__(self, symbol: str, bars: List[BacktestBar], event_bus=None):
        self.symbol = symbol
        self.bars = sorted(bars, key=lambda b: b.timestamp)
        self.event_bus = event_bus
        self.positions = {}  # {symbol: {qty, entry_price, entry_time, strategy}}
        self.closed_trades = []
        self.equity = 100000  # Start with $100k
        self.daily_pnl = 0
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        self.callbacks = []

    def subscribe(self, callback: Callable):
        """Subscribe to bar events."""
        self.callbacks.append(callback)

    def run(self):
        """Replay all bars, execute strategy logic."""
        logger.info(f"Starting backtest: {self.symbol} ({len(self.bars)} bars)")

        for i, bar in enumerate(self.bars):
            # Notify subscribers (strategies evaluate here)
            for callback in self.callbacks:
                callback(bar)

            # Check for exits
            self._check_exits(bar)

        # Close remaining positions
        if self.bars:
            last_bar = self.bars[-1]
            for symbol in list(self.positions.keys()):
                self._close_position(symbol, last_bar.close, last_bar.timestamp, "backtest_end")

        # Generate report
        return self._generate_report()

    def _check_exits(self, bar: BacktestBar):
        """Check if any positions should exit."""
        if bar.symbol not in self.positions:
            return

        pos = self.positions[bar.symbol]
        entry_price = pos["entry_price"]
        entry_time = pos["entry_time"]

        # Example exit rules:
        # 1. Stop loss hit
        stop_loss_pct = 0.01  # 1%
        if bar.low <= entry_price * (1 - stop_loss_pct):
            self._close_position(bar.symbol, entry_price * (1 - stop_loss_pct), bar.timestamp, "stop_loss")
            return

        # 2. Profit target hit
        profit_target_pct = 0.015  # 1.5%
        if bar.high >= entry_price * (1 + profit_target_pct):
            self._close_position(bar.symbol, entry_price * (1 + profit_target_pct), bar.timestamp, "profit_target")
            return

        # 3. Max hold time (2 hours = 8 candles on 15m)
        max_hold = timedelta(hours=2)
        if bar.timestamp - entry_time > max_hold:
            self._close_position(bar.symbol, bar.close, bar.timestamp, "max_hold")
            return

    def _close_position(self, symbol: str, exit_price: float, timestamp: datetime, reason: str):
        """Close a position and record P&L."""
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        qty = pos["qty"]
        entry_price = pos["entry_price"]
        pnl = (exit_price - entry_price) * qty
        pnl_pct = (exit_price - entry_price) / entry_price

        self.closed_trades.append({
            "symbol": symbol,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "qty": qty,
            "entry_time": pos["entry_time"],
            "exit_time": timestamp,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "reason": reason,
            "strategy": pos.get("strategy", "unknown"),
        })

        self.equity += pnl
        self.daily_pnl += pnl
        self.trade_count += 1
        if pnl > 0:
            self.win_count += 1
        else:
            self.loss_count += 1

        if self.event_bus:
            self.event_bus.position_closed(
                symbol=symbol,
                qty=qty,
                entry_price=entry_price,
                exit_price=exit_price,
                pnl=pnl,
                pnl_pct=pnl_pct,
                reason=reason,
            )

        del self.positions[symbol]
        logger.info(f"Closed {symbol}: entry=${entry_price:.2f} exit=${exit_price:.2f} P&L=${pnl:.2f}")

    def open_position(self, symbol: str, qty: int, entry_price: float, timestamp: datetime, strategy: str):
        """Open a position."""
        if symbol in self.positions:
            return  # Already open

        self.positions[symbol] = {
            "qty": qty,
            "entry_price": entry_price,
            "entry_time": timestamp,
            "strategy": strategy,
        }

        if self.event_bus:
            self.event_bus.position_opened(
                symbol=symbol,
                side="buy",
                qty=qty,
                entry_price=entry_price,
                strategy=strategy,
            )

        logger.info(f"Opened {symbol}: {qty} @ ${entry_price:.2f} ({strategy})")

    def _generate_report(self) -> Dict:
        """Generate backtest report."""
        if not self.closed_trades:
            return {
                "symbol": self.symbol,
                "bars": len(self.bars),
                "trades": 0,
                "status": "no trades"
            }

        wins = [t for t in self.closed_trades if t["pnl"] > 0]
        losses = [t for t in self.closed_trades if t["pnl"] < 0]

        total_pnl = sum(t["pnl"] for t in self.closed_trades)
        win_rate = len(wins) / len(self.closed_trades) * 100 if self.closed_trades else 0
        avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0
        profit_factor = sum(t["pnl"] for t in wins) / abs(sum(t["pnl"] for t in losses)) if losses else 0

        report = {
            "symbol": self.symbol,
            "bars": len(self.bars),
            "trades": len(self.closed_trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate_pct": win_rate,
            "total_pnl": total_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "final_equity": self.equity,
            "return_pct": (self.equity - 100000) / 100000 * 100,
        }

        logger.info(f"Backtest Report: {json.dumps(report, indent=2)}")
        return report


class MockDataGenerator:
    """Generate realistic mock OHLCV data for testing."""

    @staticmethod
    def generate_range_bound(
        symbol: str,
        start_price: float,
        num_bars: int,
        volatility: float = 0.005,
        trend: float = 0.0,
    ) -> List[BacktestBar]:
        """Generate range-bound price data (good for scalping)."""
        import random

        bars = []
        current_price = start_price
        base_time = datetime(2024, 1, 1, 9, 30, 0)

        for i in range(num_bars):
            # Random walk with drift
            daily_return = random.gauss(trend, volatility)
            open_price = current_price
            close_price = open_price * (1 + daily_return)

            # High/low with some range
            high = max(open_price, close_price) * (1 + abs(random.gauss(0, volatility)))
            low = min(open_price, close_price) * (1 - abs(random.gauss(0, volatility)))

            volume = int(1_000_000 + random.gauss(0, 100_000))

            bar = BacktestBar(
                symbol=symbol,
                timestamp=base_time + timedelta(minutes=5 * i),
                open_=open_price,
                high=high,
                low=low,
                close=close_price,
                volume=volume,
            )
            bars.append(bar)
            current_price = close_price

        return bars

    @staticmethod
    def generate_trending(
        symbol: str,
        start_price: float,
        num_bars: int,
        direction: str = "up",  # "up" or "down"
    ) -> List[BacktestBar]:
        """Generate trending price data (good for momentum)."""
        import random

        bars = []
        current_price = start_price
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        trend = 0.001 if direction == "up" else -0.001

        for i in range(num_bars):
            daily_return = random.gauss(trend, 0.003)
            open_price = current_price
            close_price = open_price * (1 + daily_return)

            high = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.002)))
            low = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.002)))

            volume = int(1_000_000 + random.gauss(0, 100_000))

            bar = BacktestBar(
                symbol=symbol,
                timestamp=base_time + timedelta(minutes=5 * i),
                open_=open_price,
                high=high,
                low=low,
                close=close_price,
                volume=volume,
            )
            bars.append(bar)
            current_price = close_price

        return bars

    @staticmethod
    def generate_spike_fade(
        symbol: str,
        start_price: float,
        num_bars: int,
    ) -> List[BacktestBar]:
        """Generate spike and fade pattern (good for news fades)."""
        import random

        bars = []
        current_price = start_price
        base_time = datetime(2024, 1, 1, 9, 30, 0)

        for i in range(num_bars):
            # 10% chance of spike
            if random.random() < 0.1:
                spike_direction = 1 if random.random() < 0.5 else -1
                spike_size = random.gauss(0.03, 0.01)  # 3% avg spike
                open_price = current_price * (1 + spike_direction * spike_size)
            else:
                open_price = current_price

            # Fade back toward mean
            close_price = open_price * random.gauss(0.995, 0.005)
            high = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.001)))
            low = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.001)))

            volume = int(1_000_000 + random.gauss(0, 100_000))

            bar = BacktestBar(
                symbol=symbol,
                timestamp=base_time + timedelta(minutes=5 * i),
                open_=open_price,
                high=high,
                low=low,
                close=close_price,
                volume=volume,
            )
            bars.append(bar)
            current_price = close_price

        return bars
