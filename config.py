import os
from dotenv import load_dotenv

load_dotenv()

ALPACA_API_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
ALPACA_BASE_URL = os.getenv("APCA_API_BASE_URL", "https://paper-trading.alpaca.markets")

if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    raise ValueError("Missing API credentials. Set APCA_API_KEY_ID and APCA_API_SECRET_KEY in .env")
