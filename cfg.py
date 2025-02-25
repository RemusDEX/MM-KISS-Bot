import os


REMUS_ADDRESS = '0x067e7555f9ff00f5c4e9b353ad1f400e2274964ea0942483fae97363fd5d7958'
STARKNET_RPC = 'https://starknet-mainnet.public.blastapi.io/rpc/v0_7'
NETWORK = 'MAINNET'

WALLET_ADDRESS = 0x463de332da5b88a1676bfb4671dcbe4cc1a9147c46300a1658ed43a22d830c3
# PRIVATE_KEY=
# PUBLIC_KEY=

SOURCE_DATA = {
    1: 'https://data-api.binance.vision/api/v3/aggTrades?symbol=ETHUSDC'
    # 2: 'https://data-api.binance.vision/api/v3/aggTrades?symbol=ETHUSDC'
    # 3: 'https://data-api.binance.vision/api/v3/aggTrades?symbol=ETHUSDC'
}

MARKET_MAKER_CFG = {
    1: { # market_id = 1
        'target_relative_distance_from_FP': 0.001,
        'max_error_relative_distance_from_FP': 0.001,
        'order_dollar_size': 10 * 10**18, # in $
        'minimal_remaining_quote_size': 5, # in $
    }
}

MAX_FEE = 9122241938326667
SLEEPER_SECONDS_BETWEEN_REQUOTING = 5
        

DECIMALS = {
    0x49d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7: 18,  # ETH
    0x53c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8: 6,  # USDC
    0x4718f5a0fc34cc1af16a1cdee98ffb20c31f5cd61d6ab07201858f4287c938d: 18,  # STRK
}
