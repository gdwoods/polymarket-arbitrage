# Execution Module Setup

This module places arbitrage trades on Polymarket using the CLOB API.

## Prerequisites

1. **Wallet with USDC on Polygon** – Your funder address must hold USDC and position tokens.
2. **Polymarket account** – EOA or Polymarket.com (Magic/Google).
3. **Polygon Chain ID** – 137 (mainnet)

## Environment Variables

Create a `.env` file in the project root:

```bash
POLYMARKET_PRIVATE_KEY=0x...
POLYMARKET_SIGNATURE_TYPE=1
POLYMARKET_FUNDER=0x...
```

## First-Time Setup

1. Derive API credentials: `python3 -m polymarket_app.execution.setup`
2. Save the output to .env
3. Approve tokens for the CLOB contract on Polygon

## Usage

```python
from polymarket_app.execution import ExecutionClient
client = ExecutionClient.from_env()
client.execute_buy_both(opportunity, size=10, dry_run=True)
```

## Risks

- Non-atomic fills – One leg may fill and the other not.
- Slippage – Best bid/ask can move.
- Start small; fees can eat small profits.