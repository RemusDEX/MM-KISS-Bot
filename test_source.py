import unittest
from unittest.mock import patch
import requests_mock
from source import SourceManager

class TestSourceManager(unittest.TestCase):
    def setUp(self):
        """Set up test data and initialize SourceManager."""
        self.source_data = {
            1: "https://api.example.com/market/1",
            2: "https://api.example.com/market/2"
        }
        self.source_manager = SourceManager(self.source_data)

    @requests_mock.Mocker()
    def test_fetch_price_success(self, mock_request):
        """Test fetch_price with a successful API response."""
        
        mock_data = [
            {"T": 1638316800, "p": 100.0},
            {"T": 1638316801, "p": 101.0}
        ]
        mock_request.get(self.source_data[1], json=mock_data)

        
        price = self.source_manager.fetch_price(1)

        
        self.assertEqual(price, 101.0)  # Latest price should be 101.0

    @requests_mock.Mocker()
    def test_fetch_price_failure(self, mock_request):
        """Test fetch_price with a failed API request."""
        
        mock_request.get(self.source_data[1], status_code=500)

        
        price = self.source_manager.fetch_price(1)

       
        self.assertIsNone(price)  # Should return None on failure

    def test_aggregate_price(self):
        """Test aggregate_price with a list of prices."""
        prices = [100.0, 101.0, 102.0]
        aggregated_price = self.source_manager.aggregate_price(prices)

        
        self.assertEqual(aggregated_price, 101.0)  # Average should be 101.0

    def test_aggregate_price_empty_list(self):
        """Test aggregate_price with an empty list."""
        prices = []
        aggregated_price = self.source_manager.aggregate_price(prices)

        
        self.assertEqual(aggregated_price, 0.0)  # Should return 0.0 for an empty list

    @requests_mock.Mocker()
    def test_get_fair_price_success(self, mock_request):
        """Test get_fair_price with a successful API response."""
        
        mock_data = [
            {"T": 1638316800, "p": 100.0},
            {"T": 1638316801, "p": 101.0}
        ]
        mock_request.get(self.source_data[1], json=mock_data)

        
        fair_price = self.source_manager.get_fair_price(1)

        
        self.assertEqual(fair_price, 101.0)  # Fair price should be 101.0

    @requests_mock.Mocker()
    def test_get_fair_price_failure(self, mock_request):
        """Test get_fair_price with a failed API request."""
        
        mock_request.get(self.source_data[1], status_code=500)

        
        fair_price = self.source_manager.get_fair_price(1)

        
        self.assertEqual(fair_price, 0.0)  # Should return 0.0 on failure

if __name__ == "__main__":
    unittest.main()





