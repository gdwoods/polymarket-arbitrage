# Polymarket Arbitrage App

A quantitative arbitrage detection and monitoring system for Polymarket prediction markets, built on the mathematical frameworks described in the research paper **"Unravelling the Probabilistic Forest: Arbitrage in Prediction Markets"** (arXiv:2508.03474).

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DATA PIPELINE                                     │
│  Gamma API (markets)  │  CLOB REST (order books)  │  WebSocket (realtime) │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     ARBITRAGE DETECTION                                  │
│  Layer 1: Single-condition (YES+NO ≠ $1)     ← Fast, milliseconds       │
│  Layer 2: Multi-condition / combinatorial    ← Integer programming      │
│  Layer 3: Bregman projection (optimal trade) ← Frank-Wolfe algorithm     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     EXECUTION (scaffolded)                               │
│  VWAP estimation │ Position sizing │ Order submission (py-clob-client)   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the arbitrage scanner (CLI)
python -m polymarket_app.scanner [limit]   # default 30 markets

# Lower min profit to surface near-arbitrage (edit config.py or scanner.py)

# Launch the monitoring dashboard
streamlit run polymarket_app/dashboard.py
```

## Key Endpoints

| API | Base URL | Purpose |
|-----|----------|----------|
| Gamma | `https://gamma-api.polymarket.com` | Market discovery, metadata |
| CLOB | `https://clob.polymarket.com` | Order books, prices, orders |
| WebSocket | `wss://ws-subscriptions-clob.polymarket.com/ws/` | Real-time orderbook |

## References

- [arXiv:2508.03474](https://arxiv.org/abs/2508.03474) - Unravelling the Probabilistic Forest
- [arXiv:1606.02825](https://arxiv.org/abs/2508.03474) - Arbitrage-Free Combinatorial Market Making via Integer Programming
- [Polymarket Docs](https://docs.polymarket.com)

## Execution

To place trades programmatically, use the execution module:

```bash
# 1. Set env vars (see polymarket_app/execution/README.md)
# 2. Derive API credentials
python3 -m polymarket_app.execution.setup

# 3. Use in code
python3 -c "
from polymarket_app.execution import ExecutionClient
from polymarket_app.arbitrage.single_condition import ArbitrageOpportunity
# ... get opportunity from scanner, then:
# client = ExecutionClient.from_env()
# result = client.execute_buy_both(opp, size=10, dry_run=True)
"
```

## Roadmap (Toward Production)

| Layer | Status | Description |
|-------|--------|-------------|
| Data pipeline | ✅ | Gamma + CLOB REST |
| Single-condition arb | ✅ | YES + NO ≠ $1 |
| Bregman projection | ✅ Scaffold | `polymarket_app/arbitrage/bregman.py` |
| Frank-Wolfe + IP | 📋 | Gurobi/PuLP for multi-condition |
| WebSocket real-time | 📋 | `wss://ws-subscriptions-clob.polymarket.com/ws/` |
| Execution (py-clob-client) | 📋 | Place orders, VWAP simulation |

## Disclaimer

This is for educational and research purposes. Trading involves risk. The research paper reported $40M extracted by sophisticated actors; execution speed, capital, and infrastructure matter significantly.
