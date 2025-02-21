from typing import Any, Tuple
from starknet_py.net.account.account import Account
from starknet_py.contract import Contract




class RemusManager:
          
    def init(self, address: str, provider: Account) -> Contract:
        return Contract.from_address(address= address, provider = provider)
    
    @staticmethod
    def get_quote_contract(market_cfg: Any, provider: Account) -> Contract:
        return Contract.from_address(address= market_cfg[1]['quote_token'], provider= provider)
    
    @staticmethod
    def get_base_contract(market_cfg: Any, provider: Account) -> Contract:
        return Contract.from_address(address= market_cfg[1]['base_token'], provider=provider)
    
    @staticmethod
    def get_config(contract: Contract) -> Tuple:
        return contract.functions['get_all_market_configs'].call()