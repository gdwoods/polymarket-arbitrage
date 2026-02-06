"""Configuration and constants."""

# Polymarket API endpoints
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"
CLOB_WS = "wss://ws-subscriptions-clob.polymarket.com/ws/"

# Arbitrage detection thresholds (from research paper)
MIN_PROFIT_THRESHOLD = 0.03  # 3% minimum - smaller edges eaten by fees/slippage
PRICE_DEVIATION_THRESHOLD = 0.02  # |VWAP_yes + VWAP_no - 1.0| > 0.02
LIQUIDITY_PCT_CAP = 0.5  # Max 50% of order book depth to avoid moving market

# Frank-Wolfe parameters (from research)
ALPHA = 0.9  # Extract at least 90% of available arbitrage
INITIAL_EPSILON = 0.1  # 10% contraction for gradient boundedness
CONVERGENCE_THRESHOLD = 1e-6
MAX_ITERATIONS = 150
