# Stock Simulator

Paper trading simulator using Alpaca API. Test strategies with fake money ($100k starting balance).

## Setup

### 1. Get Alpaca API Keys
1. Sign up at https://app.alpaca.markets/signup (free)
2. Go to Dashboard → API Keys
3. Copy your API Key and Secret Key

### 2. Install & Configure
```bash
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and add your API credentials:
```
APCA_API_KEY_ID=your_key
APCA_API_SECRET_KEY=your_secret
APCA_API_BASE_URL=https://paper-trading.alpaca.markets
```

### 3. Run
```bash
python trader.py
```

## Usage

### View Account Status
```python
from trader import StockSimulator

trader = StockSimulator()
account = trader.get_account()
print(f"Cash: ${account['cash']:.2f}")
print(f"Portfolio: ${account['portfolio_value']:.2f}")
```

### Place Orders
```python
# Buy 10 shares of AAPL
order = trader.buy("AAPL", 10)

# Sell 5 shares of AAPL
order = trader.sell("AAPL", 5)
```

### View Positions
```python
positions = trader.get_positions()
for pos in positions:
    print(f"{pos['symbol']}: {pos['qty']} shares, P&L: ${pos['unrealized_pl']:.2f}")
```

### Get Historical Data
```python
bars = trader.get_bars("AAPL", days=30)
for bar in bars:
    print(f"{bar['timestamp']}: Close ${bar['close']:.2f}")
```

## Paper Trading Details

- **Starting Balance:** $100,000 (fake)
- **Commissions:** None
- **Market Hours:** Standard US stock market hours
- **Real Data:** Real-time market data, fake money

## Next Steps

- Build strategies (buy/hold, RSI, moving average, etc.)
- Backtest against historical data
- Track P&L across multiple bets
- Create alerts for price targets
