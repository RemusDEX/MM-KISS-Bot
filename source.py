from typing import Dict, List, Optional
import requests
import logging


class SourceManager:
    def __init__(self, source_data: Dict[int, str]):

        self.source_data = source_data

    def fetch_price(self, market_id: int) -> Optional[float]:

        if market_id not in self.source_data:
            logging.error(f"No source URL configured for market_id={market_id}.")
            return None

        try:
            response = requests.get(self.source_data[market_id])
            response.raise_for_status()
            data = response.json()

            latest_price = float(sorted(data, key=lambda x: x["T"])[-1]["p"])
            logging.info(
                f"Successfully fetched price for market_id={market_id}: {latest_price}."
            )
            return latest_price
        except Exception as e:
            logging.error(f"Failed to fetch price for market_id={market_id}: {str(e)}")
            return None

    def aggregate_price(self, prices: List[float]) -> float:

        if not prices:
            logging.warning("No prices provided for aggregation.")
            return 0.0
        return sum(prices) / len(prices)

    def get_fair_price(self, market_id: int) -> float:

        price = self.fetch_price(market_id)
        if price is None:
            logging.error(f"Unable to calculate fair price for market_id={market_id}.")
            return 0.0

        return price
