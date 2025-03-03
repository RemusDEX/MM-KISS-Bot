import os
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import Dict

# Load environment variables
load_dotenv()

MAX_FEE = 9122241938326667
SOURCE_DATA = {
    1: 'https://data-api.binance.vision/api/v3/aggTrades?symbol=ETHUSDC'
    # 2: 'https://data-api.binance.vision/api/v3/aggTrades?symbol=ETHUSDC'
    # 3: 'https://data-api.binance.vision/api/v3/aggTrades?symbol=ETHUSDC'
}

@dataclass
class Config:
    remus_address: str = os.getenv("REMUS_ADDRESS")
    starknet_rpc: str = os.getenv("STARKNET_RPC")
    network: str = os.getenv("NETWORK")
    private_key: str = os.getenv("PRIVATE_KEY")
    public_key: str = os.getenv("PUBLIC_KEY")
    wallet_address: int = int(os.getenv("WALLET_ADDRESS"), 16)
    account_password: str = os.getenv("ACCOUNT_PASSWORD")
    path_to_keystore: str = os.getenv("PATH_TO_KEYSTORE")

@dataclass
class TokenConfig:
    decimals: Dict[str, int] = field(default_factory=lambda: {
        0x49d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7: 18,  # ETH
        0x53c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8: 6,   # USDC
        0x4718f5a0fc34cc1af16a1cdee98ffb20c31f5cd61d6ab07201858f4287c938d: 18,  # STRK
    })

@dataclass
class MarketConfig:
    market_maker_cfg: Dict[int, Dict[str, float]] = field(
        default_factory=lambda: {
            1: {  # market_id = 1
                'target_relative_distance_from_FP': 0.001,
                'max_error_relative_distance_from_FP': 0.001,
                'order_dollar_size': 10 * 10**18,  # in $
                'minimal_remaining_quote_size': 5,  # in $
            }
        }
    )

env_config = Config()
token_config = TokenConfig()
market_config = MarketConfig()
