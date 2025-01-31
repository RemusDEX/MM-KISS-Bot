REMUS_ADDRESS = '0x04e1ac8fe63b465a583740a684aeff3589428d50869b79da2dd296c380ee4bd8'
STARKNET_RPC = 'https://starknet-sepolia.public.blastapi.io/rpc/v0_7'
NETWORK = 'SEPOLIA'

WALLET_ADDRESS=
PRIVATE_KEY=
PUBLIC_KEY=

SOURCE_DATA = {
    1: 'https://data-api.binance.vision/api/v3/aggTrades?symbol=ETHUSDC'
    # 2: 'https://data-api.binance.vision/api/v3/aggTrades?symbol=ETHUSDC'
    # 3: 'https://data-api.binance.vision/api/v3/aggTrades?symbol=ETHUSDC'
}

MARKET_MAKER_CFG = {
    1: { # market_id = 1
        'target_relative_distance_from_FP': 0.001,
        'max_error_relative_distance_from_FP': 0.001,
        # 'max_error_relative_distance_from_FP': 0.00,
        'order_dollar_size': 1000 * 10**18, # in $
        'minimal_remaining_quote_size': 100, # in $
    }
}

MAX_FEE=91222419383266677
