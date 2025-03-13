import os
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import Dict

# Load environment variables
load_dotenv()

MAX_FEE = 251222419383266
SOURCE_DATA = {
    1: 'https://data-api.binance.vision/api/v3/aggTrades?symbol=ETHUSDC',
    2: 'https://data-api.binance.vision/api/v3/aggTrades?symbol=STRKUSDC',
    3: 'https://data-api.binance.vision/api/v3/aggTrades?symbol=BTCUSDC'
}
SLEEPER_SECONDS_BETWEEN_REQUOTING = 5

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
        0x03fe2b97c1fd336e750087d68b9b867997fd64a2661ff3ca5a7c771641e8e7ac: 8 # wBTC
    })

@dataclass
class MarketConfig:
    market_maker_cfg: Dict[int, Dict[str, float]] = field(
        default_factory=lambda: {
            1: {  # market_id = 1 ETH/USDC
                #best orders
                'target_relative_distance_from_FP': 0.001, # where best order is created 
                'max_relative_distance_from_FP': 0.003, # too far from FP to be considered best (it is considered deep)
                'min_relative_distance_from_FP': 0.0005, # too close to FP to exist -> if closer kill the order

                'order_dollar_size': 200 * 10**18,  # in $
                'minimal_remaining_quote_size': 100,  # in $
                'max_number_of_orders_per_side': 3
            },
            # 2: {  # market_id = 2 STRK/USDC
            #     #best orders
            #     'target_relative_distance_from_FP': 0.001, # where best order is created 
            #     'max_relative_distance_from_FP': 0.003, # too far from FP to be considered best (it is considered deep)
            #     'min_relative_distance_from_FP': 0.0005, # too close to FP to exist -> if closer kill the order

            #     'order_dollar_size': 200 * 10**18,  # in $
            #     'minimal_remaining_quote_size': 100,  # in $
            #     'max_number_of_orders_per_side': 3
            # },
            # 3: {  # market_id = 3 wBTC/USDC
            #     #best orders
            #     'target_relative_distance_from_FP': 0.001, # where best order is created 
            #     'max_relative_distance_from_FP': 0.003, # too far from FP to be considered best (it is considered deep)
            #     'min_relative_distance_from_FP': 0.0005, # too close to FP to exist -> if closer kill the order

            #     'order_dollar_size': 200 * 10**8,  # in $
            #     'minimal_remaining_quote_size': 100,  # in $
            #     'max_number_of_orders_per_side': 3
            # },
        }
    )

env_config = Config()
token_config = TokenConfig()
market_config = MarketConfig()
