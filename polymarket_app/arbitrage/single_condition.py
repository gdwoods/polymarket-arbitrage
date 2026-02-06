"""
Single-condition arbitrage detection.

Layer 1: Fast check - do YES + NO prices sum to $1?
- Buy arb: sum < 1 -> buy both, guaranteed $1 payout
- Sell arb: sum > 1 -> sell both, guaranteed < $1 cost
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..data.models import ConditionPrices

from ..config import MIN_PROFIT_THRESHOLD
from ..data.models import ConditionPrices, Market, OrderBook


@dataclass
class ArbitrageOpportunity:
    """Detected arbitrage opportunity."""
    market_id: str
    question: str
    slug: str
    event_slug: str
    direction: str
    price_yes: float
    price_no: float
    sum_prices: float
    profit_margin: float
    token_id_yes: str
    token_id_no: str
    order_book_yes: Optional[OrderBook] = None
    order_book_no: Optional[OrderBook] = None
    end_date: str = ""

    @property
    def max_profit_per_dollar(self) -> float:
        return self.profit_margin

    def max_extractable_usd(self, max_size: float | None = None) -> float | None:
        if not self.order_book_yes or not self.order_book_no:
            return None
        yes_depth = sum(s for _, s in self.order_book_yes.asks)
        no_depth = sum(s for _, s in self.order_book_no.asks)
        if self.direction == "sell_both":
            yes_depth = sum(s for _, s in self.order_book_yes.bids)
            no_depth = sum(s for _, s in self.order_book_no.bids)
        cap = min(yes_depth, no_depth)
        if max_size is not None:
            cap = min(cap, max_size)
        return self.profit_margin * cap


def detect_single_condition_arbitrage(
    market: Market,
    min_profit: float = MIN_PROFIT_THRESHOLD,
    use_order_book: bool = True,
    clob_prices: Optional[dict[str, "ConditionPrices"]] = None,
) -> list[ArbitrageOpportunity]:
    if clob_prices:
        buy_prices = clob_prices.get("buy")
        sell_prices = clob_prices.get("sell")
    elif use_order_book:
        ob_prices = market.get_order_book_prices()
        buy_prices = ob_prices["buy"] if ob_prices else market.get_prices()
        sell_prices = ob_prices["sell"] if ob_prices else market.get_prices()
    else:
        gp = market.get_prices()
        buy_prices = sell_prices = gp

    if not buy_prices or not sell_prices:
        return []

    opps = []
    if buy_prices.arbitrage_down and buy_prices.profit_margin >= min_profit:
        opps.append(
            ArbitrageOpportunity(
                market_id=market.id,
                question=market.question,
                slug=market.slug,
                event_slug=market.event_slug,
                end_date=getattr(market, "end_date", "") or "",
                direction="buy_both",
                price_yes=buy_prices.price_yes,
                price_no=buy_prices.price_no,
                sum_prices=buy_prices.sum_prices,
                profit_margin=buy_prices.profit_margin,
                token_id_yes=buy_prices.token_id_yes,
                token_id_no=buy_prices.token_id_no,
                order_book_yes=market.order_book_yes,
                order_book_no=market.order_book_no,
            )
        )
    if sell_prices.arbitrage_up and sell_prices.profit_margin >= min_profit:
        opps.append(
            ArbitrageOpportunity(
                market_id=market.id,
                question=market.question,
                slug=market.slug,
                event_slug=market.event_slug,
                end_date=getattr(market, "end_date", "") or "",
                direction="sell_both",
                price_yes=sell_prices.price_yes,
                price_no=sell_prices.price_no,
                sum_prices=sell_prices.sum_prices,
                profit_margin=sell_prices.profit_margin,
                token_id_yes=sell_prices.token_id_yes,
                token_id_no=sell_prices.token_id_no,
                order_book_yes=market.order_book_yes,
                order_book_no=market.order_book_no,
            )
        )
    return opps