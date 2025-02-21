"""Main script for the Market Maker bot."""

from typing import Any, Tuple
import argparse
import asyncio
import logging
import requests

from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.contract import Contract
from starknet_py.net.account.account import Account
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starknet_py.net.models.chains import StarknetChainId

try:
    from cfg import (
        REMUS_ADDRESS, STARKNET_RPC, WALLET_ADDRESS, SOURCE_DATA, NETWORK,
        MARKET_MAKER_CFG, MAX_FEE, DECIMALS
    )
except ImportError as e:
    logging.error("Failed to import configuration module: %s", str(e))
    REMUS_ADDRESS = STARKNET_RPC = WALLET_ADDRESS = SOURCE_DATA = None
    NETWORK = MARKET_MAKER_CFG = MAX_FEE = DECIMALS = None

PATH_TO_KEYSTORE = "keystore.json"

def setup_logging(log_level: str):
    """Configures logging for the application."""
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=getattr(logging, log_level.upper(), "INFO"), format=log_format)

def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Main async script for the application.")
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Set the logging level")
    parser.add_argument("--account-password", type=str, default="",
                        help="Set the account password")
    return parser.parse_args()

def get_account(account_password: str) -> Account:
    """Get a market maker's account."""
    client = FullNodeClient(node_url=STARKNET_RPC)
    account = Account(
        client=client,
        address=WALLET_ADDRESS,
        key_pair=KeyPair.from_keystore(PATH_TO_KEYSTORE, account_password),
        chain=StarknetChainId[NETWORK]
    )
    logging.info("Successfully loaded account.")
    return account

def get_market_cfg(all_remus_cfgs: Any, market_id: int) -> Tuple[Any, Any]:
    """Retrieve market configuration."""
    market_cfg = [x for x in all_remus_cfgs[0] if x[0] == market_id][0]
    market_maker_cfg = MARKET_MAKER_CFG.get(market_id)
    assert market_cfg and market_maker_cfg
    logging.info("Successfully loaded market configs for market_id=%s.", market_id)
    return market_cfg, market_maker_cfg

async def claim_tokens(market_cfg, remus_contract) -> None:
    """Claims unclaimed tokens."""
    for token_address in [market_cfg[1]['base_token'], market_cfg[1]['quote_token']]:
        claimable = await remus_contract.functions['get_claimable'].call(
            token_address=token_address, user_address=WALLET_ADDRESS
        )
        logging.info("Claimable amount is %s for token %s.", claimable, token_address)
        if claimable[0]:
            await remus_contract.functions['claim'].invoke_v1(
                token_address=token_address, amount=claimable[0], max_fee=MAX_FEE
            )
            logging.info("Claim done.")

def get_optimal_quotes(asks, bids, market_cfg):
    """Calculates optimal quotes based on current market conditions."""
    to_be_canceled = []
    to_be_created = []
    base_decimals = DECIMALS[market_cfg[1]['base_token']]
    for side in [asks, bids]:
        to_be_canceled_side = []
        for order in side:
            if (order['amount_remaining'] / 10**base_decimals * order['price'] /
                    10**base_decimals) < 1:
                logging.info("Canceling order: insufficient amount %s", order['amount_remaining'])
                to_be_canceled_side.append(order)
                continue
        to_be_canceled.extend(to_be_canceled_side)
    logging.info("Optimal quotes calculated: to_be_canceled: %s, to_be_created: %s",
                 len(to_be_canceled), len(to_be_created))
    return to_be_canceled, to_be_created

async def async_main():
    """Main async execution function."""
    args = parse_arguments()
    setup_logging(args.log_level)
    logging.info("Starting Simple Stupid Market Maker")
    account = get_account(args.account_password)
    remus_contract = await Contract.from_address(address=REMUS_ADDRESS, provider=account)
    all_remus_cfgs = await remus_contract.functions['get_all_market_configs'].call()
    while True:
        await asyncio.sleep(1)
        for market_id in [x[0] for x in all_remus_cfgs[0] if x[0] in MARKET_MAKER_CFG]:
            try:
                market_cfg, _ = get_market_cfg(all_remus_cfgs, market_id)
                await claim_tokens(market_cfg, remus_contract)
                response = requests.get(SOURCE_DATA[market_id], timeout=10)
                fair_price = float(sorted(response.json(), key=lambda x: x['T'])[-1]['p'])
                logging.info("Fair price queried: %s", fair_price)
            except (requests.RequestException, ValueError) as err:
                logging.error("An error occurred: %s", str(err))

if __name__ == "__main__":
    asyncio.run(async_main())
