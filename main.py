from typing import Any, Tuple
import argparse
import asyncio
import logging
import requests
import sys
from remus import RemusManager

from starknet_py.net.full_node_client import FullNodeClient
# from starknet_py.hash.selector import get_selector_from_name
# from starknet_py.net.client_models import Call
from starknet_py.contract import Contract
from starknet_py.net.account.account import Account
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starknet_py.net.models.chains import StarknetChainId
from starknet_py.net.client_errors import ClientError
from starknet_py.transaction_errors import TransactionNotReceivedError
# from starknet_py.utils.typed_data import EnumParameter
# from starknet_py.net.client_models import ResourceBounds

from config import token_config, env_config, market_config, MAX_FEE, SOURCE_DATA, SLEEPER_SECONDS_BETWEEN_REQUOTING



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
    return parser.parse_args()


def get_account() -> Account:
    """Get a market makers account."""
    client = FullNodeClient(node_url = env_config.starknet_rpc)
    account = Account(
        client = client,
        address = env_config.wallet_address,
        key_pair = KeyPair.from_keystore(env_config.path_to_keystore, env_config.account_password),
        chain = StarknetChainId[env_config.network]
    )
    logging.info("Succesfully loaded account.")
    return account


def get_market_cfg(all_remus_cfgs: Any, market_id: int) -> Tuple[Any, Any]:
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
            user_address = env_config.wallet_address
        )
        logging.info(f'Claimable amount is {claimable} for token {hex(token_address)}.')
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
    balance_base = await base_token_contract.functions['balance_of'].call(account=env_config.wallet_address)
    amount_remaining_base = sum(x['amount_remaining'] for x in asks)
    total_possible_position_base = balance_base[0] + amount_remaining_base

    balance_quote = await quote_token_contract.functions['balance_of'].call(account=env_config.wallet_address)
    amount_remaining_quote = sum(x['amount_remaining'] for x in bids)
    total_possible_position_quote = balance_quote[0] + amount_remaining_quote

    logging.debug(f"Queried user balance for market_id: {market_cfg[0]} as ({total_possible_position_base}, {total_possible_position_quote})")
    logging.debug(f"Queried user balance for market_id: {market_cfg[0]}")

    return total_possible_position_base, total_possible_position_quote


def get_optimal_quotes(asks, bids, market_maker_cfg, market_cfg, fair_price):
    """
    If an existing quote has lower than market_maker_cfg['minimal_remaining_quote_size'] quantity, it is requoted.
    
    Optimal quote is in market_maker_cfg['target_relative_distance_from_FP'] distance from the FP, where FP is binance price.
    The order is never perfect and market_maker_cfg['max_distance_from_FP'] from optimal quote price level is allowed, meaning
    that an old best quote is considered deep quote and new best is created if the distance is outside of what is ok.

    If the Best quote gets too close to FP, less than market_maker_cfg['min_distance_from_FP'] distance, it is canceled.
    """
    to_be_canceled = []
    to_be_created = []

    base_decimals = token_config.decimals[market_cfg[1]['base_token']]  # for example ETH
    quote_decimals = token_config.decimals[market_cfg[1]['quote_token']]  # for example USDC
    
    for side, side_name in [(asks, 'ask'), (bids, 'bid')]:
        to_be_canceled_side = []
        to_be_created_side = []
    
        for order in side:
            # If the remaining order size is too small requote (cancel order)
            if order['amount_remaining'] / 10**base_decimals * order['price'] / 10**base_decimals < market_maker_cfg['minimal_remaining_quote_size']:
                logging.info(f"Canceling order because of insufficient amount. amount: {order['amount_remaining']}")
                logging.debug(f"Canceling order because of insufficient amount. order: {order}")
                to_be_canceled_side.append(order)
                continue
            if (
                (
                    (side_name == 'bid')
                    and
                    ((1 - market_maker_cfg['min_relative_distance_from_FP']) * fair_price < order['price'] / 10**base_decimals)
                )
                or
                (
                    (side_name == 'ask')
                    and
                    (order['price'] / 10**base_decimals < (1 + market_maker_cfg['min_relative_distance_from_FP']) * fair_price)
                )
            ):
                logging.info(f"Canceling order because too close to FP. fair_price: {fair_price}, order price: {order['price'] / 10**base_decimals}")
                logging.debug(f"Canceling order because too close to FP. order: {order}")
                to_be_canceled_side.append(order)
        # If there is too many orders in the market that are not being canceled, cancel those with the most distant price from FP
        # to a point that only the "allowed" number of orders is being kept.
        if len(side) - len(to_be_canceled_side) > market_maker_cfg['max_number_of_orders_per_side']:
            # assumes "side" (e.g. asks and bids) are ordered from the best to the deepest
            to_be_canceled_side.extend(
                [order for order in side if order not in to_be_canceled_side][market_maker_cfg['max_number_of_orders_per_side']:]
            )
        to_be_canceled.extend(to_be_canceled_side)
    
        # Create best order if there is no best order
        remaining = [order for order in side if order not in to_be_canceled]
        ordered_remaining = sorted(remaining, key=lambda x: x['price'] if side_name=='ask' else -x['price'])
        if (
            (not ordered_remaining)
            or
            (
                (side_name == 'bid')
                and
                (order['price'] / 10**base_decimals < (1 - market_maker_cfg['max_relative_distance_from_FP']) * fair_price)
            )
            or
            (
                (side_name == 'ask')
                and
                ((1 + market_maker_cfg['max_relative_distance_from_FP']) * fair_price < order['price'] / 10**base_decimals)
            )
        ):
            tick_size = market_cfg[1]['tick_size']
            base_decimals_ = 18 if market_cfg[0] == 3 else base_decimals
            if side_name == 'ask':
                optimal_price = int(fair_price * (1 + market_maker_cfg['target_relative_distance_from_FP']) * 10**base_decimals_)
                optimal_price = optimal_price // tick_size
                optimal_price = optimal_price * tick_size + tick_size
            else:
                optimal_price = int(fair_price * (1 - market_maker_cfg['target_relative_distance_from_FP']) * 10**base_decimals_)
                optimal_price = optimal_price // tick_size
                optimal_price = optimal_price * tick_size
            optimal_amount = market_maker_cfg['order_dollar_size'] / (optimal_price / 10**base_decimals_)
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


async def update_delete_quotes(
    account: Account,
    market_cfg,
    remus_contract,
    to_be_canceled,
    to_be_created,
    base_token_contract,
    quote_token_contract
) -> int:
    nonce = await account.get_nonce()
    number_of_txs_used = 0
    for i, order in enumerate(to_be_canceled):
        await remus_contract.functions['delete_maker_order'].invoke_v1(
            maker_order_id=order['maker_order_id'],
            max_fee=MAX_FEE,
            nonce = nonce + i
        )
        logging.info(f"Canceling: {order['maker_order_id']}")
        number_of_txs_used += 1

    return nonce + number_of_txs_used

async def update_best_quotes(
    account: Account,
    market_id,
    market_cfg,
    remus_contract,
    to_be_canceled,
    to_be_created,
    base_token_contract,
    quote_token_contract,
    nonce # nonce pushed here is the first UNused nonce
) -> int:
    base_decimals = token_config.decimals[market_cfg[1]['base_token']]  # for example ETH
    quote_decimals = token_config.decimals[market_cfg[1]['quote_token']]  # for example USDC
    
    for i, order in enumerate(to_be_created):
        if order['order_side'] == 'ask':
            target_token_address = market_cfg[1]['base_token']
            order_side = 'Ask'
            token_contract = base_token_contract
        else:
            target_token_address = market_cfg[1]['quote_token']
            order_side = 'Bid'
            token_contract = quote_token_contract
    
        approve_amount = order['amount'] if order_side == 'Ask' else order['amount'] * order['price'] / 10**base_decimals

        await token_contract.functions['approve'].invoke_v1(
            spender = int(env_config.remus_address, 16),
            amount = int(approve_amount),
            max_fee = MAX_FEE,
            nonce = nonce + i * 2
        )
        logging.info(f"Approving: {approve_amount}")

        logging.info("Soon to sumbit order: q: %s, p: %s, s: %s", order['amount'], order['price'], order_side)
        logging.debug("Soon to sumbit order: %s", dict(
            market_id = market_id,
            target_token_address = target_token_address,
            order_price = order['price'],
            order_size = order['amount'],
            order_side = (order_side, None),
            order_type = ('Basic', None),
            time_limit = ('GTC', None),
            max_fee = MAX_FEE,
            nonce = nonce + i * 2 + 1
        ))
        await remus_contract.functions['submit_maker_order'].invoke_v1(
            market_id = market_id,
            target_token_address = target_token_address,
            order_price = order['price'],
            order_size = order['amount'],
            order_side = (order_side, None),
            order_type = ('Basic', None),
            time_limit = ('GTC', None),
            max_fee = MAX_FEE,
            nonce = nonce + i * 2 + 1
        )
        logging.info(f"Submitting order: q: {order['amount']}, p: {order['price']}, s: {order_side}")
    logging.info('Done with order changes')


def pretty_print_orders(asks, bids):
    logging.info('Pretty printed current orders.')
    for ask in sorted(asks, key=lambda x: -x['price']):
        logging.info('\t\t%s; %s', ask['price'] / 10**18, ask['amount_remaining'] / 10**18)
    logging.info('XXX')
    for bid in sorted(bids, key=lambda x: -x['price']):
        logging.info('\t\t%s; %s', bid['price'] / 10**18, bid['amount_remaining'] / 10**18)


async def async_main():
    """Main async execution function."""
    args = parse_arguments()
    setup_logging(args.log_level)

    logging.info("Starting Simple Stupid Market Maker")

    account = get_account()

    # FIXME: This was half done, yet merged to master. Keeping it for now for the sake of making
    # the code run (without having enough time to fix things).
    # TODO: the remus_manager is f*** up, not sure whether to remove and redo completely.
    remus_contract = await Contract.from_address(address = env_config.remus_address, provider = account)

    all_remus_cfgs = await remus_contract.functions['get_all_market_configs'].call()

    # remus_manager = RemusManager(account, env_config, remus_contract, all_remus_cfgs)
    
    while True:
        await asyncio.sleep(SLEEPER_SECONDS_BETWEEN_REQUOTING)
        for market_id in [x[0] for x in all_remus_cfgs[0] if x[0] in market_config.market_maker_cfg]:
            try:
                market_cfg, market_maker_cfg = get_market_cfg(all_remus_cfgs, market_id)

                # 1) Claim tokens
                # TODO ideally the claim would happen after the order deletion.
                await claim_tokens(market_cfg, remus_contract)

                # 2) Get prices
                r = requests.get(SOURCE_DATA[market_id])
                fair_price = float(sorted(r.json(), key = lambda x: x['T'])[-1]['p'])
                logging.info('Fair price queried: %s.', fair_price)

                # 3) Get orders
                my_orders = await remus_contract.functions['get_all_user_orders'].call(user=env_config.wallet_address)

                bids = [x for x in my_orders[0] if x['market_id'] == market_id and x['order_side'].variant == 'Bid']
                asks = [x for x in my_orders[0] if x['market_id'] == market_id and x['order_side'].variant == 'Ask']
                bids = sorted(bids, key = lambda x: -x['price'])
                asks = sorted(asks, key = lambda x: -x['price'])
                logging.debug(f'My remaining orders queried: {bids}, {asks}.')
                pretty_print_orders(asks, bids)

                # 4) Get position (balance of + open orders)
                # TODO: the remus_manager is messed up, it has to be debugged and fixed
                # base_token_contract = await remus_manager.get_base_contract()
                # quote_token_contract = await remus_manager.get_quote_contract()

                base_token_contract = await Contract.from_address(address = market_cfg[1]['base_token'], provider = account)
                quote_token_contract = await Contract.from_address(address = market_cfg[1]['quote_token'], provider = account)

                total_possible_position_base, total_possible_position_quote = await get_position(
                    market_cfg, account, asks, bids, base_token_contract, quote_token_contract
                )

                # 5) Calculate optimal quotes
                to_be_canceled, to_be_created = get_optimal_quotes(asks, bids, market_maker_cfg, market_cfg, fair_price)

                # 6) update quotes
                nonce = await update_delete_quotes(account, market_cfg, remus_contract, to_be_canceled, to_be_created, base_token_contract, quote_token_contract)
                assert nonce is not None
                assert nonce != 0
                await update_best_quotes(account, market_id, market_cfg, remus_contract, to_be_canceled, to_be_created, base_token_contract, quote_token_contract, nonce)

                logging.info("Application running successfully.")
                # assert False
            except ClientError as e:
                # ClientError can be
                # starknet_py.net.client_errors.ClientError: Client failed with code 63. Message: An unexpected error occurred. Data: HTTP status server error (502 Bad Gateway) for url (https://alpha-mainnet.starknet.io/gateway/add_transaction)
                # Client failed with code 55. Message: Account validation failed. Data: Invalid transaction nonce of contract at address 0x0463de332da5b88a1676bfb4671dcbe4cc1a9147c46300a1658ed43a22d830c3. Account nonce: 0x0000000000000000000000000000000000000000000000000000000000022046; got: 0x0000000000000000000000000000000000000000000000000000000000022043
                logging.error("A ClientError error occurred: %s", str(e), exc_info=True)
                logging.error("Restarting in 5 seconds!")

                await asyncio.sleep(5)

                # Often the main fails because of the Account not having a proper nonce. So let's re-initialize it.
                account = get_account()
                remus_contract = await Contract.from_address(address = env_config.remus_address, provider = account)

            except TransactionNotReceivedError as e:
                # starknet_py.transaction_errors.TransactionNotReceivedError: Transaction was not received on Starknet.

                logging.error("A ClientError error occurred: %s", str(e), exc_info=True)
                logging.error("Restarting in 5 seconds!")

                account = get_account()
                remus_contract = await Contract.from_address(address = env_config.remus_address, provider = account)

            except Exception as e:
                logging.error("An error occurred: %s", str(e), exc_info=True)
                logging.error("Starting to cancel all - wait.")

                await asyncio.sleep(5)

                # Often the main fails because of the Account not having a proper nonce. So let's re-initialize it.
                account = get_account()
                remus_contract = await Contract.from_address(address = env_config.remus_address, provider = account)

                # Get all existing orders
                logging.error("Starting to cancel all - get_all_user_orders.")
                my_orders = await remus_contract.functions['get_all_user_orders'].call(user=env_config.wallet_address)
                logging.error("Starting to cancel all - my_orders:{%s}.", my_orders)

                # Cancel all existing orders
                nonce = await account.get_nonce()
                for i, order in enumerate(my_orders[0]):
                    await (await remus_contract.functions['delete_maker_order'].invoke_v1(
                        maker_order_id=order['maker_order_id'],
                        max_fee=int(MAX_FEE/10),
                        nonce = nonce + i
                    )).wait_for_acceptance()

                # Waiting a little and checking existing orders
                logging.error("Ending cancel all - wait before exit.")
                await asyncio.sleep(15)
                my_orders = await remus_contract.functions['get_all_user_orders'].call(user=env_config.wallet_address)
                logging.error("Ending cancel all - remaining my_orders:{%s}.", my_orders)

                #Claiming unclaimed
                logging.error("Ending cancel all - claiming unclaimed.")
                for market_id in market_config.market_maker_cfg.keys():
                    try:
                        market_cfg, market_maker_cfg = get_market_cfg(all_remus_cfgs, market_id)
                        await claim_tokens(market_cfg, remus_contract)
                    except:
                        logging.error("An error while closing session occured: %s", str(e), exc_info=True)

                logging.error("Ending cancel all - FINISHED.")

                # sys.exit(1)


if __name__ == "__main__":
    asyncio.run(async_main())

