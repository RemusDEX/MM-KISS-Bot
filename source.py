from typing import Dict, List, Optional
import requests
import logging


class SourceManager:
    """
    A class to manage fetching and aggregating prices from various market sources.

    Attributes:
        source_data (Dict[int, str]): A dictionary mapping market IDs to their respective API URLs.
    """

    def __init__(self, source_data: Dict[int, str]) -> None:
        """
        Initialize the SourceManager with a dictionary of market IDs and their API URLs.

        Args:
            source_data (Dict[int, str]): A dictionary where keys are market IDs and values are API URLs.
        """
        self.source_data = source_data

    def fetch_price(self, market_id: int) -> Optional[float]:
        """
        Fetch the latest price for a given market ID from the configured source.

        Args:
            market_id (int): The ID of the market to fetch the price for.

        Returns:
            Optional[float]: The latest price if successful, otherwise None.
        """
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
        """
        Aggregate a list of prices into a single value (e.g., average).

        Args:
            prices (List[float]): A list of prices to aggregate.

        Returns:
            float: The aggregated price (average of the list).
        """
        if not prices:
            logging.warning("No prices provided for aggregation.")
            return 0.0
        return sum(prices) / len(prices)

    def get_fair_price(self, market_id: int) -> float:
        """
        Calculate the fair price for a given market ID.

        Args:
            market_id (int): The ID of the market to calculate the fair price for.

        Returns:
            float: The calculated fair price. Returns 0.0 if the price cannot be fetched.
        """
        price = self.fetch_price(market_id)
        if price is None:
            logging.error(f"Unable to calculate fair price for market_id={market_id}.")
            return 0.0

        return price