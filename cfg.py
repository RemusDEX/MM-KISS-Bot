"""
Configuration module for MM-KISS-Bot.

This module loads environment variables using dotenv and defines configuration classes.
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Main configuration class for bot settings."""
    # pylint: disable=too-few-public-methods
    REMUS_ADDRESS = os.getenv("REMUS_ADDRESS")
    STARKNET_RPC = os.getenv("STARKNET_RPC")
    NETWORK = os.getenv("NETWORK")
    PRIVATE_KEY = os.getenv("PRIVATE_KEY")
    PUBLIC_KEY = os.getenv("PUBLIC_KEY")

class MarketMakerConfig:
    """Configuration class for market maker settings."""
    # pylint: disable=too-few-public-methods
    DECIMALS = int(os.getenv("DECIMALS", "18"))  # Ensure correct type conversion

class AdvancedConfig:
    """Advanced configuration settings."""
    # pylint: disable=too-few-public-methods
    MARKET_MAKER_CFG = os.getenv("MARKET_MAKER_CFG")
