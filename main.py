from typing import Any, Tuple
import argparse
import asyncio
import logging
import requests
import sys

from starknet_py.net.full_node_client import FullNodeClient
# from starknet_py.hash.selector import get_selector_from_name
# from starknet_py.net.client_models import Call
from starknet_py.contract import Contract
from starknet_py.net.account.account import Account
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starknet_py.net.models.chains import StarknetChainId
# from starknet_py.utils.typed_data import EnumParameter
# from starknet_py.net.client_models import ResourceBounds

from config import token_config, env_config, market_config, WALLET_ADDRESS, MAX_FEE, SOURCE_DATA



PATH_TO_KEYSTORE = "keystore.json"



def setup_logging(log_level: str):
    """Configures logging for the application."""
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=getattr(logging, log_level.upper(), "INFO"), format=log_format)

    
def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Main async script for the application.")
    parser.add_argument(
        "--log-level",
        type = str,
        default = "INFO",
        choices = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help = "Set the logging level"
    )
    parser.add_argument(
        "--account-password",
        type = str,
        default = "",
        help = "Set the account password"
    )
    return parser.parse_args()


def get_account(account_password: str) -> Account:
    """Get a market makers account."""
    client = FullNodeClient(node_url = env_config.starknet_rpc)
    account = Account(
        client = client,
        address = WALLET_ADDRESS,
        key_pair = KeyPair.from_keystore(PATH_TO_KEYSTORE, account_password),
        chain = StarknetChainId[env_config.network]
    )
    logging.info("Succesfully loaded account.")
    return account


def get_market_cfg(all_remus_cfgs: Any, market_id: int) -> Tuple[Any, Any]:
    market_id = 1
    market_cfg = all_remus_cfgs[0][0]
    market_maker_cfg = market_config.market_maker_cfg[market_id]
    assert market_maker_cfg
    market_cfg = [x for x in all_remus_cfgs[0] if x[0] == market_id][0]
    assert market_cfg
    logging.info(f"Succesfully loaded market configs for market_id={market_id}.")
    return market_cfg, market_maker_cfg


async def claim_tokens(market_cfg, remus_contract) -> None:
    """
    Claims the unclaims tokens.

    TODO: This implementation is quite inefficient since the claim of USDC happens too often across many markets.
    (within the overall picture of the bot being run across markets).
    """
    for token_address in [market_cfg[1]['base_token'], market_cfg[1]['quote_token']]:
        claimable = await remus_contract.functions['get_claimable'].call(
            token_address = token_address,
            user_address = WALLET_ADDRESS
        )
        logging.info(f'Claimable amount is {claimable} for token {token_address}.')
        if claimable[0]:
            logging.info(f'Claiming')
            claim = await remus_contract.functions['claim'].invoke_v1(
                token_address = token_address,
                amount = claimable[0],
                max_fee = MAX_FEE
            )
        logging.info(f'Claim done.')


async def get_position(market_cfg, account, asks, bids, base_token_contract, quote_token_contract):
    """
    MM bot position is its balance plus the remaining amount on present orders.
    # base_token_contract - mETH
    # quote_token_contract - mUSDC
    """
    balance_base = await base_token_contract.functions['balance_of'].call(account=WALLET_ADDRESS)
    amount_remaining_base = sum(x['amount_remaining'] for x in asks)
    total_possible_position_base = balance_base[0] + amount_remaining_base
    #
    balance_quote = await quote_token_contract.functions['balance_of'].call(account=WALLET_ADDRESS)
    amount_remaining_quote = sum(x['amount_remaining'] for x in bids)
    total_possible_position_quote = balance_quote[0] + amount_remaining_quote

    logging.debug(f"Queried user balance for market_id: {market_cfg[0]} as ({total_possible_position_base}, {total_possible_position_quote})")
    logging.debug(f"Queried user balance for market_id: {market_cfg[0]}")

    return total_possible_position_base, total_possible_position_quote


def get_optimal_quotes(asks, bids, market_maker_cfg, market_cfg, fair_price):
    """
    If an existing quote has lower than market_maker_cfg['minimal_remaining_quote_size'] quantity, it is requoted.
    
    Optimal quote is in market_maker_cfg['target_relative_distance_from_FP'] distance from the FP, where FP is binance price.
    The order is never perfect and market_maker_cfg['max_error_relative_distance_from_FP'] from optimal quote price level is allowed, meaning
    that an old quote is canceled and new one created if the distance is outside of what is ok.
    """
    to_be_canceled = []
    to_be_created = []

    base_decimals = token_config.decimals[market_cfg[1]['base_token']]  # for example ETH
    quote_decimals = token_config.decimals[market_cfg[1]['quote_token']]  # for example USDC
    
    for side, side_name in [(asks, 'ask'), (bids, 'bid')]:
        to_be_canceled_side = []
        to_be_created_side = []
    
        for order in side:
            if order['amount_remaining'] / 10**base_decimals * order['price'] / 10**base_decimals < market_maker_cfg['minimal_remaining_quote_size']:
                logging.info(f"Canceling order because of insufficient amount. amount: {order['amount_remaining']}")
                logging.debug(f"Canceling order because of insufficient amount. order: {order}")
                to_be_canceled_side.append(order)
                continue
            if (
                (1 - market_maker_cfg['max_error_relative_distance_from_FP'] > order['price'] / 10**base_decimals / fair_price)
                or
                (order['price'] / 10**base_decimals / fair_price > 1 + market_maker_cfg['max_error_relative_distance_from_FP'])
            ):
                logging.info(f"Canceling order because of incorrect price. fair_price: {fair_price}, order price: {order['price'] / 10**base_decimals}")
                logging.debug(f"Canceling order because of incorrect price. order: {order}")
                to_be_canceled_side.append(order)
        # If there is too many orders in the market that are not being canceled, cancel them at random. This can happen due to transactions failures.
        if len(side) - len(to_be_canceled_side) > 1:
            remainers = []
            for order in side:
                if order not in to_be_canceled_side:
                    remainers.append(order)
            to_be_canceled_side.extend(remainers[1:])
        to_be_canceled.extend(to_be_canceled_side)
    
        # Create order if there is no order
        if len(to_be_canceled_side) == len(side):
            if side_name == 'ask':
                optimal_price = int(fair_price * (1 + market_maker_cfg['target_relative_distance_from_FP']) * 10**base_decimals)
                optimal_price = optimal_price // market_cfg[1]['tick_size']
                optimal_price = optimal_price * market_cfg[1]['tick_size'] + market_cfg[1]['tick_size']
            else:
                optimal_price = int(fair_price * (1 - market_maker_cfg['target_relative_distance_from_FP']) * 10**base_decimals)
                optimal_price = optimal_price // market_cfg[1]['tick_size']
                optimal_price = optimal_price * market_cfg[1]['tick_size']
    
            optimal_amount = market_maker_cfg['order_dollar_size'] / (optimal_price / 10**base_decimals) 
            optimal_amount = optimal_amount // market_cfg[1]['lot_size']
            optimal_amount = optimal_amount * market_cfg[1]['lot_size']
    
            order = {
                'order_side': side_name,
                'amount': int(optimal_amount),
                'price': optimal_price
            }
            to_be_created.append(order)
    logging.info(f"Optimal quotes calculated: to_be_canceled: {len(to_be_canceled)}, to_be_created: {len(to_be_created)}")
    logging.debug(f"Optimal quotes calculated: to_be_canceled: {to_be_canceled}, to_be_created: {to_be_created}")
    return to_be_canceled, to_be_created


async def update_quotes(account: Account, market_cfg, remus_contract, to_be_canceled, to_be_created, base_token_contract, quote_token_contract):
    
    base_decimals = token_config.decimals[market_cfg[1]['base_token']]  # for example ETH
    quote_decimals = token_config.decimals[market_cfg[1]['quote_token']]  # for example USDC
    
    nonce = await account.get_nonce()
    for i, order in enumerate(to_be_canceled):
        (await remus_contract.functions['delete_maker_order'].invoke_v1(
            maker_order_id=order['maker_order_id'],
            max_fee=MAX_FEE,
            nonce = nonce + i
        )).wait_for_acceptance()
        logging.info(f"Canceling: {order['maker_order_id']}")
    
    for i, order in enumerate(to_be_created):
        if order['order_side'] == 'ask':
            target_token_address = market_cfg[1]['base_token']
            order_side = 'Ask'
            token_contract = base_token_contract
        else:
            target_token_address = market_cfg[1]['quote_token']
            order_side = 'Bid'
            token_contract = quote_token_contract
    
        approve_amount = order['amount'] if order_side == 'Bid' else order['amount'] * order['price'] / 10**base_decimals
        if order_side == 'Bid':
            approve_amount = 1000 * 10**base_decimals
        await (await token_contract.functions['approve'].invoke_v1(
            spender=int(env_config.remus_address, 16),
            amount = int(approve_amount),
            max_fee=MAX_FEE,
            nonce = nonce + len(to_be_canceled) + i * 2
        )).wait_for_acceptance()
        logging.info(f"Approving: {order['amount']}")

        logging.info(f"Soon to sumbit order: q: {order['amount']}, p: {order['price']}, s: {order_side}")
        await (await remus_contract.functions['submit_maker_order'].invoke_v1(
            market_id=1,
            target_token_address=target_token_address,
            order_price = order['price'],
            order_size = order['amount'],
            order_side = (order_side, None),
            order_type = ('Basic', None),
            time_limit = ('GTC', None),
            max_fee=MAX_FEE,
            nonce = nonce + len(to_be_canceled) + i * 2 + 1
        )).wait_for_acceptance()
        logging.info(f"Submitting order: q: {order['amount']}, p: {order['price']}, s: {order_side}")
    logging.info('Done with order changes')


async def async_main():
    """Main async execution function."""
    args = parse_arguments()
    setup_logging(args.log_level)

    logging.info("Starting Simple Stupid Market Maker")

    account = get_account(args.account_password)
    remus_contract = await Contract.from_address(address = env_config.remus_address, provider = account)
    all_remus_cfgs = await remus_contract.functions['get_all_market_configs'].call()
    
    while True:
        await asyncio.sleep(1)  # Example async operation
        for market_id in [x[0] for x in all_remus_cfgs[0] if x[0] in market_config.market_maker_cfg]:
            try:
                market_cfg, market_maker_cfg = get_market_cfg(all_remus_cfgs, market_id)

                # 1) Claim tokens
                # TODO ideally the claim would happen after the order deletion.
                await claim_tokens(market_cfg, remus_contract)

                # 2) Get prices
                r = requests.get(SOURCE_DATA[market_id])
                fair_price = float(sorted(r.json(), key = lambda x: x['T'])[-1]['p'])
                logging.info(f'Fair price queried: {fair_price}.')

                # 3) Get orders
                my_orders = await remus_contract.functions['get_all_user_orders'].call(user=WALLET_ADDRESS)

                bids = [x for x in my_orders[0] if x['market_id'] == market_id and x['order_side'].variant == 'Bid']
                asks = [x for x in my_orders[0] if x['market_id'] == market_id and x['order_side'].variant == 'Ask']
                logging.debug(f'My remaining orders queried: {bids}, {asks}.')

                # 4) Get position (balance of + open orders)
                base_token_contract = await Contract.from_address(address = market_cfg[1]['base_token'], provider = account)
                quote_token_contract = await Contract.from_address(address = market_cfg[1]['quote_token'], provider = account)
                total_possible_position_base, total_possible_position_quote = await get_position(
                    market_cfg, account, asks, bids, base_token_contract, quote_token_contract
                )

                # 5) Calculate optimal quotes
                to_be_canceled, to_be_created = get_optimal_quotes(asks, bids, market_maker_cfg, market_cfg, fair_price)

                # 6) update quotes
                await update_quotes(account, market_cfg, remus_contract, to_be_canceled, to_be_created, base_token_contract, quote_token_contract)
                
                logging.info("Application running successfully.")
            except Exception as e:
                logging.error("An error occurred: %s", str(e), exc_info=True)
                # sys.exit(1)

if __name__ == "__main__":
    asyncio.run(async_main())
