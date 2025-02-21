import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class Config:
    REMUS_ADDRESS: str = os.getenv("REMUS_ADDRESS")
    STARKNET_RPC: str = os.getenv("STARKNET_RPC")
    NETWORK: str = os.getenv("NETWORK")
    PRIVATE_KEY: str = os.getenv("PRIVATE_KEY")
    PUBLIC_KEY: str = os.getenv("PUBLIC_KEY")

@dataclass
class TokenConfig:
    DECIMALS: int = int(os.getenv("DECIMALS", 18))

@dataclass
class MarketConfig:
    MARKET_MAKER_CFG: str = os.getenv("MARKET_MAKER_CFG")

config = Config()
token_config = TokenConfig()
market_config = MarketConfig()
