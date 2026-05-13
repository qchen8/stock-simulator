"""
Stock Simulator - Paper Trading with Alpaca API
"""
import os
from alpaca_trade_api.rest import REST
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL


class StockSimulator:
    def __init__(self):
        """Initialize Alpaca REST client (paper trading mode)"""
        self.api = REST(
            key_id=ALPACA_API_KEY,
            secret_key=ALPACA_SECRET_KEY,
            base_url=ALPACA_BASE_URL,
        )

    def get_account(self):
        """Fetch account info"""
        account = self.api.get_account()
        return {
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "buying_power": float(account.buying_power),
            "trading_status": account.status,
        }

    def get_positions(self):
        """Get current open positions"""
        positions = self.api.get_positions()
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
        order = self.api.submit_order(
            symbol=symbol,
            qty=qty,
            side="buy",
            type="market",
            time_in_force="day",
        )
        return {
            "order_id": order.id,
            "symbol": order.symbol,
            "qty": float(order.qty),
            "side": order.side,
            "status": order.status,
            "submitted_at": str(order.submitted_at),
        }

    def sell(self, symbol, qty):
        """Place a market sell order"""
        order = self.api.submit_order(
            symbol=symbol,
            qty=qty,
            side="sell",
            type="market",
            time_in_force="day",
        )
        return {
            "order_id": order.id,
            "symbol": order.symbol,
            "qty": float(order.qty),
            "side": order.side,
            "status": order.status,
            "submitted_at": str(order.submitted_at),
        }

    def get_orders(self, status="all"):
        """Get order history"""
        orders = self.api.get_orders(status=status)
        result = []
        for order in orders:
            result.append({
                "order_id": order.id,
                "symbol": order.symbol,
                "qty": float(order.qty),
                "side": order.side,
                "price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "status": order.status,
                "submitted_at": str(order.submitted_at),
                "filled_at": str(order.filled_at) if order.filled_at else None,
            })
        return result

    def get_bars(self, symbol, days=30):
        """Fetch historical bars"""
        bars = self.api.get_barset(symbol, "day", limit=days)
        if not bars:
            return []
        result = []
        for bar in bars[symbol]:
            result.append({
                "timestamp": str(bar.t),
                "open": float(bar.o),
                "high": float(bar.h),
                "low": float(bar.l),
                "close": float(bar.c),
                "volume": int(bar.v),
            })
        return result


if __name__ == "__main__":
    trader = StockSimulator()
    
    print("=== Account Status ===")
    account = trader.get_account()
    print(f"Cash: ${account['cash']:.2f}")
    print(f"Portfolio Value: ${account['portfolio_value']:.2f}")
    print(f"Buying Power: ${account['buying_power']:.2f}")
    print(f"Status: {account['trading_status']}")
    
    print("\n=== Current Positions ===")
    positions = trader.get_positions()
    if positions:
        for pos in positions:
            print(f"{pos['symbol']}: {pos['qty']} @ ${pos['current_price']:.2f} ({pos['unrealized_plpc']:.2f}%)")
    else:
        print("No positions")
    
    print("\n=== Recent Orders ===")
    orders = trader.get_orders(status="closed")
    if orders:
        for order in orders[:5]:
            print(f"{order['side'].upper()} {order['qty']} {order['symbol']} @ ${order['price']} - {order['status']}")
    else:
        print("No closed orders")
