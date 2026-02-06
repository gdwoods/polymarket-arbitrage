"""
Execution module for placing arbitrage trades on Polymarket.

Requires: py-clob-client, wallet with USDC, Polymarket API credentials.
See polymarket_app/execution/README.md for setup.
"""

from .client import ExecutionClient

__all__ = ["ExecutionClient"]