"""
Event system for broadcasting trade and signal events.
Allows real-time monitoring and logging of all activity.
"""
import json
import logging
from datetime import datetime
from typing import Callable, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types for the trading bot."""
    SIGNAL_GENERATED = "signal_generated"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELED = "order_canceled"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    STOP_LOSS_HIT = "stop_loss_hit"
    PROFIT_TARGET_HIT = "profit_target_hit"
    DAILY_LOSS_LIMIT_HIT = "daily_loss_limit_hit"
    ERROR = "error"
    MARKET_OPEN = "market_open"
    MARKET_CLOSE = "market_close"
    CANDLE_CLOSED = "candle_closed"


@dataclass
class Event:
    """Base event."""
    type: EventType
    timestamp: datetime
    data: Dict[str, Any]

    def to_dict(self):
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class EventBus:
    """
    Central event bus for broadcasting trade/signal events.
    Allows subscribers to listen for specific event types.
    """

    def __init__(self, log_file: str = None):
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.log_file = log_file
        self.event_history: List[Event] = []
        self._init_subscribers()

    def _init_subscribers(self):
        """Initialize subscriber lists for all event types."""
        for event_type in EventType:
            self.subscribers[event_type] = []

    def subscribe(self, event_type: EventType, callback: Callable):
        """Subscribe to an event type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to {event_type.value}")

    def unsubscribe(self, event_type: EventType, callback: Callable):
        """Unsubscribe from an event type."""
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(callback)

    def publish(self, event: Event):
        """Publish an event to all subscribers."""
        self.event_history.append(event)

        # Log to file
        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(event.to_json() + "\n")

        # Notify subscribers
        for callback in self.subscribers[event.type]:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

        logger.info(f"Event: {event.type.value} @ {event.timestamp.isoformat()}")

    def signal_generated(
        self,
        symbol: str,
        strategy: str,
        signal: str,  # "buy", "sell", "hold"
        score: float,
        candle_time: str,
    ):
        """Signal generated (RSI, MACD, etc triggered)."""
        self.publish(
            Event(
                type=EventType.SIGNAL_GENERATED,
                timestamp=datetime.utcnow(),
                data={
                    "symbol": symbol,
                    "strategy": strategy,
                    "signal": signal,
                    "score": score,
                    "candle_time": candle_time,
                },
            )
        )

    def order_placed(
        self,
        symbol: str,
        side: str,  # "buy" or "sell"
        qty: int,
        order_type: str,  # "market", "limit", etc
        price: float = None,
    ):
        """Order placed (submitted to broker)."""
        self.publish(
            Event(
                type=EventType.ORDER_PLACED,
                timestamp=datetime.utcnow(),
                data={
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "order_type": order_type,
                    "price": price,
                },
            )
        )

    def order_filled(
        self,
        order_id: str,
        symbol: str,
        side: str,
        qty: int,
        fill_price: float,
    ):
        """Order filled (executed at broker)."""
        self.publish(
            Event(
                type=EventType.ORDER_FILLED,
                timestamp=datetime.utcnow(),
                data={
                    "order_id": order_id,
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "fill_price": fill_price,
                },
            )
        )

    def position_opened(
        self,
        symbol: str,
        side: str,
        qty: int,
        entry_price: float,
        strategy: str,
    ):
        """Position opened (long or short)."""
        self.publish(
            Event(
                type=EventType.POSITION_OPENED,
                timestamp=datetime.utcnow(),
                data={
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "entry_price": entry_price,
                    "strategy": strategy,
                },
            )
        )

    def position_closed(
        self,
        symbol: str,
        qty: int,
        entry_price: float,
        exit_price: float,
        pnl: float,
        pnl_pct: float,
        reason: str,  # "profit_target", "stop_loss", "manual", etc
    ):
        """Position closed (all or part)."""
        self.publish(
            Event(
                type=EventType.POSITION_CLOSED,
                timestamp=datetime.utcnow(),
                data={
                    "symbol": symbol,
                    "qty": qty,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "reason": reason,
                },
            )
        )

    def stop_loss_hit(
        self,
        symbol: str,
        entry_price: float,
        stop_price: float,
        loss: float,
    ):
        """Stop loss triggered."""
        self.publish(
            Event(
                type=EventType.STOP_LOSS_HIT,
                timestamp=datetime.utcnow(),
                data={
                    "symbol": symbol,
                    "entry_price": entry_price,
                    "stop_price": stop_price,
                    "loss": loss,
                },
            )
        )

    def profit_target_hit(
        self,
        symbol: str,
        entry_price: float,
        target_price: float,
        profit: float,
    ):
        """Profit target reached."""
        self.publish(
            Event(
                type=EventType.PROFIT_TARGET_HIT,
                timestamp=datetime.utcnow(),
                data={
                    "symbol": symbol,
                    "entry_price": entry_price,
                    "target_price": target_price,
                    "profit": profit,
                },
            )
        )

    def daily_loss_limit_hit(self, daily_loss: float):
        """Daily loss limit reached - stop trading."""
        self.publish(
            Event(
                type=EventType.DAILY_LOSS_LIMIT_HIT,
                timestamp=datetime.utcnow(),
                data={"daily_loss": daily_loss},
            )
        )

    def error(self, message: str, context: Dict = None):
        """Log error event."""
        self.publish(
            Event(
                type=EventType.ERROR,
                timestamp=datetime.utcnow(),
                data={"message": message, "context": context or {}},
            )
        )

    def get_history(self, event_type: EventType = None, limit: int = 100) -> List[Event]:
        """Get event history, optionally filtered by type."""
        if event_type:
            return [e for e in self.event_history if e.type == event_type][-limit:]
        return self.event_history[-limit:]

    def get_today_trades(self) -> List[Event]:
        """Get all trade-related events today (closes, opens, stops)."""
        trade_types = [
            EventType.POSITION_OPENED,
            EventType.POSITION_CLOSED,
            EventType.STOP_LOSS_HIT,
            EventType.PROFIT_TARGET_HIT,
        ]
        today = datetime.utcnow().date()
        return [
            e
            for e in self.event_history
            if e.type in trade_types and e.timestamp.date() == today
        ]
