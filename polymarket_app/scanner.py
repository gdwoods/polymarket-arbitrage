"""
CLI arbitrage scanner.

Fetches active markets, enriches with order books, and reports opportunities.
"""

import asyncio
from rich.console import Console
from rich.table import Table

from .config import MIN_PROFIT_THRESHOLD
from .data import GammaClient, ClobClient
from .data.models import Market
from .arbitrage import detect_single_condition_arbitrage


async def run_scan(limit: int = 50, min_profit: float = MIN_PROFIT_THRESHOLD) -> None:
    """Fetch markets, enrich with order books, detect arbitrage."""
    gamma = GammaClient()
    clob = ClobClient()
    console = Console()

    console.print("[bold]Polymarket Arbitrage Scanner[/bold]")
    console.print(f"Fetching up to {limit} active markets...")

    markets = await gamma.fetch_active_markets(limit=limit)
    binary = [
        m
        for m in markets
        if len(m.clob_token_ids) >= 2
        and m.clob_token_ids[0]
        and m.clob_token_ids[1]
    ]
    console.print(f"Found {len(binary)} binary markets with token IDs")

    for m in binary:
        try:
            ob_yes = await clob.get_order_book(m.clob_token_ids[0])
            ob_no = await clob.get_order_book(m.clob_token_ids[1])
            m.order_book_yes = ob_yes
            m.order_book_no = ob_no
        except Exception:
            pass
        await asyncio.sleep(0.1)

    opportunities = []
    for m in binary:
        opps = detect_single_condition_arbitrage(m, min_profit=min_profit)
        opportunities.extend(opps)

    if not opportunities:
        console.print("[yellow]No arbitrage opportunities exceeding threshold.[/yellow]")
        return

    table = Table(title="Arbitrage Opportunities")
    table.add_column("Question", style="cyan", max_width=50)
    table.add_column("Direction", style="green")
    table.add_column("YES", justify="right")
    table.add_column("NO", justify="right")
    table.add_column("Sum", justify="right")
    table.add_column("Profit %", justify="right")
    table.add_column("Max USD", justify="right")

    for o in opportunities[:20]:
        max_usd = o.max_extractable_usd()
        max_str = f"${max_usd:.2f}" if max_usd is not None else "—"
        table.add_row(
            o.question[:48] + ".." if len(o.question) > 50 else o.question,
            o.direction,
            f"{o.price_yes:.3f}",
            f"{o.price_no:.3f}",
            f"{o.sum_prices:.3f}",
            f"{o.profit_margin*100:.2f}%",
            max_str,
        )

    console.print(table)
    console.print(f"\n[green]Total: {len(opportunities)} opportunities[/green]")


def main() -> None:
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    asyncio.run(run_scan(limit=limit))


if __name__ == "__main__":
    main()
