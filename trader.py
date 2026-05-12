"""
Stock Simulator - Paper Trading with Alpaca API
"""
import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL


class StockSimulator:
    def __init__(self):
        """Initialize Alpaca trading client (paper trading mode)"""
        self.client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
        self.data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)

    def get_account(self):
        """Fetch account info"""
        account = self.client.get_account()
        return {
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "buying_power": float(account.buying_power),
            "trading_status": account.status,
        }

    def get_positions(self):
        """Get current open positions"""
        positions = self.client.get_all_positions()
        result = []
        for pos in positions:
            result.append({
                "symbol": pos.symbol,
                "qty": float(pos.qty),
                "avg_fill_price": float(pos.avg_fill_price),
                "current_price": float(pos.current_price),
                "unrealized_pl": float(pos.unrealized_pl),
                "unrealized_plpc": float(pos.unrealized_plpc),
            })
        return result

    def buy(self, symbol, qty):
        """Place a market buy order"""
        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
        )
        order = self.client.submit_order(order_request)
        return {
            "order_id": order.id,
            "symbol": order.symbol,
            "qty": float(order.qty),
            "side": order.side.value,
            "status": order.status,
            "submitted_at": str(order.submitted_at),
        }

    def sell(self, symbol, qty):
        """Place a market sell order"""
        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        order = self.client.submit_order(order_request)
        return {
            "order_id": order.id,
            "symbol": order.symbol,
            "qty": float(order.qty),
            "side": order.side.value,
            "status": order.status,
            "submitted_at": str(order.submitted_at),
        }

    def get_orders(self, status="all"):
        """Get order history"""
        orders = self.client.get_orders(status=status)
        result = []
        for order in orders:
            result.append({
                "order_id": order.id,
                "symbol": order.symbol,
                "qty": float(order.qty),
                "side": order.side.value,
                "price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "status": order.status,
                "submitted_at": str(order.submitted_at),
                "filled_at": str(order.filled_at) if order.filled_at else None,
            })
        return result

    def get_bars(self, symbol, days=30):
        """Fetch historical bars"""
        start_date = datetime.now() - timedelta(days=days)
        request = StockBarsRequest(
            symbol_or_symbols=[symbol],
            start=start_date,
            timeframe=TimeFrame.DAY,
        )
        bars = self.data_client.get_stock_bars(request)
        result = []
        for bar in bars[symbol]:
            result.append({
                "timestamp": str(bar.timestamp),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": int(bar.volume),
            })
        return result


if __name__ == "__main__":
    trader = StockSimulator()
    
    print("=== Account Status ===")
    account = trader.get_account()
    print(f"Cash: ${account['cash']:.2f}")
    print(f"Portfolio Value: ${account['portfolio_value']:.2f}")
    print(f"Buying Power: ${account['buying_power']:.2f}")
    
    print("\n=== Current Positions ===")
    positions = trader.get_positions()
    if positions:
        for pos in positions:
            print(f"{pos['symbol']}: {pos['qty']} @ ${pos['current_price']:.2f} ({pos['unrealized_plpc']:.2f}%)")
    else:
        print("No positions")
    
    print("\n=== Recent Orders ===")
    orders = trader.get_orders(status="closed")
    for order in orders[:5]:
        print(f"{order['side']} {order['qty']} {order['symbol']} @ ${order['price']} - {order['status']}")
