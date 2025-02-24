from starknet_py.contract import Contract
import asyncio

class RemusManager:
    def __init__(self, account, env_config):
        """
        Initialize the RemusManager with the given account and environment configuration.
        This method should be called only once.
        """
        self.account = account
        self.env_config = env_config
        self.remus_contract = None
        self.all_remus_cfgs = None

    async def init(self):
        """
        Initialize the Remus connection and fetch market configurations.
        This should be called only once when initializing RemusManager.
        """
        if self.remus_contract is None:
            self.remus_contract = await Contract.from_address(
                address=self.env_config.remus_address, provider=self.account
            )
            await self.get_config()

    async def get_config(self):
        """
        Fetch all market configurations from Remus.
        """
        self.all_remus_cfgs = await self.remus_contract.functions[
            'get_all_market_configs'
        ].call()

    async def get_base_contract(self, market_index=1):
        """
        Get the base token contract for the specified market index.
        """
        if not self.all_remus_cfgs:
            await self.get_config()
        market_cfg = self.all_remus_cfgs[market_index]
        base_token_contract = await Contract.from_address(
            address=market_cfg['base_token'], provider=self.account
        )
        return base_token_contract

    async def get_quote_contract(self, market_index=1):
        """
        Get the quote token contract for the specified market index.
        """
        if not self.all_remus_cfgs:
            await self.get_config()
        market_cfg = self.all_remus_cfgs[market_index]
        quote_token_contract = await Contract.from_address(
            address=market_cfg['quote_token'], provider=self.account
        )
        return quote_token_contract


