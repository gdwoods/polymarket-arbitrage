"""Data models for Polymarket markets and order books."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConditionPrices:
    """Prices for YES/NO conditions in a binary market."""
    token_id_yes: str
    token_id_no: str
    price_yes: float
    price_no: float
    outcome_yes: str = "Yes"
    outcome_no: str = "No"

    @property
    def sum_prices(self) -> float:
        """YES + NO should equal 1.0 for arbitrage-free pricing."""
        return self.price_yes + self.price_no

    @property
    def arbitrage_up(self) -> bool:
        """Can sell both for > $1 (guaranteed profit)."""
        return self.sum_prices > 1.0

    @property
    def arbitrage_down(self) -> bool:
        """Can buy both for < $1 (guaranteed profit)."""
        return self.sum_prices < 1.0

    @property
    def profit_margin(self) -> float:
        """Max of buy-arb and sell-arb profit per $1."""
        if self.arbitrage_up:
            return self.sum_prices - 1.0
        if self.arbitrage_down:
            return 1.0 - self.sum_prices
        return 0.0


@dataclass
class OrderBook:
    """Order book for a single token."""
    asset_id: str
    bids: list[tuple[float, float]]  # (price, size)
    asks: list[tuple[float, float]]

    def vwap_buy(self, size: float) -> Optional[float]:
        """Volume-weighted average price to buy given size."""
        remaining = size
        cost = 0.0
        for price, ask_size in sorted(self.asks):
            fill = min(remaining, ask_size)
            cost += price * fill
            remaining -= fill
            if remaining <= 0:
                break
        if remaining > 0:
            return None  # Insufficient liquidity
        return cost / size if size > 0 else 0.0

    def vwap_sell(self, size: float) -> Optional[float]:
        """Volume-weighted average price to sell given size."""
        remaining = size
        revenue = 0.0
        for price, bid_size in sorted(self.bids, reverse=True):
            fill = min(remaining, bid_size)
            revenue += price * fill
            remaining -= fill
            if remaining <= 0:
                break
        if remaining > 0:
            return None
        return revenue / size if size > 0 else 0.0

    def best_bid(self) -> Optional[float]:
        return max((p for p, _ in self.bids), default=None)

    def best_ask(self) -> Optional[float]:
        return min((p for p, _ in self.asks), default=None)


@dataclass
class Market:
    """Polymarket market with condition prices and order books."""
    id: str
    question: str
    slug: str
    event_slug: str  # Event slug for /event/{event_slug} URLs (multi-market events)
    condition_id: str
    outcomes: list[str]
    outcome_prices: list[float]
    clob_token_ids: list[str]
    order_book_yes: Optional[OrderBook] = None
    order_book_no: Optional[OrderBook] = None
    end_date: str = ""  # Resolution/expiration date (ISO), for filtering

    def get_prices(self) -> Optional[ConditionPrices]:
        """Build ConditionPrices from Gamma outcome data."""
        return self._gamma_prices()

    def _gamma_prices(self) -> Optional[ConditionPrices]:
        """Prices from Gamma API outcomePrices."""
        if len(self.outcomes) < 2 or len(self.outcome_prices) < 2 or len(self.clob_token_ids) < 2:
            return None
        return ConditionPrices(
            token_id_yes=self.clob_token_ids[0],
            token_id_no=self.clob_token_ids[1],
            price_yes=float(self.outcome_prices[0]),
            price_no=float(self.outcome_prices[1]),
            outcome_yes=self.outcomes[0],
            outcome_no=self.outcomes[1],
        )

    def get_order_book_prices(self) -> Optional[dict[str, ConditionPrices]]:
        """
        Tradeable prices from order books when available.
        Returns {"buy": ConditionPrices (best ask), "sell": ConditionPrices (best bid)}
        or None if order books missing/incomplete.
        """
        if not self.order_book_yes or not self.order_book_no:
            return None
        best_ask_yes = self.order_book_yes.best_ask()
        best_ask_no = self.order_book_no.best_ask()
        best_bid_yes = self.order_book_yes.best_bid()
        best_bid_no = self.order_book_no.best_bid()
        if best_ask_yes is None or best_ask_no is None or best_bid_yes is None or best_bid_no is None:
            return None
        return {
            "buy": ConditionPrices(
                token_id_yes=self.clob_token_ids[0],
                token_id_no=self.clob_token_ids[1],
                price_yes=best_ask_yes,
                price_no=best_ask_no,
                outcome_yes=self.outcomes[0] if self.outcomes else "Yes",
                outcome_no=self.outcomes[1] if len(self.outcomes) > 1 else "No",
            ),
            "sell": ConditionPrices(
                token_id_yes=self.clob_token_ids[0],
                token_id_no=self.clob_token_ids[1],
                price_yes=best_bid_yes,
                price_no=best_bid_no,
                outcome_yes=self.outcomes[0] if self.outcomes else "Yes",
                outcome_no=self.outcomes[1] if len(self.outcomes) > 1 else "No",
            ),
        }
