"""CLOB API client for order books and prices."""

import httpx
from .models import OrderBook, ConditionPrices


class ClobClient:
    """Client for Polymarket CLOB - order books, prices, orders."""

    def __init__(self, base_url: str = "https://clob.polymarket.com"):
        self.base_url = base_url.rstrip("/")

    async def get_price(self, token_id: str, side: str = "buy", timeout: float = 10.0) -> float | None:
        """Get current price for a token. Returns None on 404 or error."""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(
                    f"{self.base_url}/price",
                    params={"token_id": token_id, "side": side},
                )
                r.raise_for_status()
                data = r.json()
                p = data.get("price")
                return float(p) if p is not None else None
        except Exception:
            return None

    async def get_order_book(self, token_id: str, timeout: float = 10.0) -> OrderBook | None:
        """Get order book for a token. Raises on HTTP error."""
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(
                f"{self.base_url}/book",
                params={"token_id": token_id},
            )
            r.raise_for_status()
            data = r.json()

        def parse_levels(levels: list) -> list[tuple[float, float]]:
            out = []
            for L in levels or []:
                if isinstance(L, dict):
                    price = float(L.get("price", 0))
                    size = float(L.get("size", L.get("volume", 0)))
                else:
                    price, size = float(L[0]), float(L[1])
                if price > 0 and size > 0:
                    out.append((price, size))
            return out

        if data.get("error"):
            return None
        bids = parse_levels(data.get("bids", []))
        asks = parse_levels(data.get("asks", []))
        return OrderBook(asset_id=token_id, bids=bids, asks=asks)

    async def get_order_book_safe(self, token_id: str) -> OrderBook | None:
        """Get order book, returning None on 404 or error."""
        try:
            return await self.get_order_book(token_id)
        except Exception:
            return None

    async def get_clob_prices(
        self,
        token_id_yes: str,
        token_id_no: str,
        outcomes: list[str] | None = None,
    ) -> dict[str, ConditionPrices] | None:
        """
        Get buy/sell prices from CLOB /price endpoint (works for more tokens than /book).
        Returns {"buy": ConditionPrices, "sell": ConditionPrices} or None.
        """
        buy_yes = await self.get_price(token_id_yes, side="buy")
        buy_no = await self.get_price(token_id_no, side="buy")
        sell_yes = await self.get_price(token_id_yes, side="sell")
        sell_no = await self.get_price(token_id_no, side="sell")
        if buy_yes is None or buy_no is None or sell_yes is None or sell_no is None:
            return None
        o_yes = (outcomes or ["Yes", "No"])[0]
        o_no = (outcomes or ["Yes", "No"])[1] if len(outcomes or []) > 1 else "No"
        return {
            "buy": ConditionPrices(
                token_id_yes=token_id_yes,
                token_id_no=token_id_no,
                price_yes=buy_yes,
                price_no=buy_no,
                outcome_yes=o_yes,
                outcome_no=o_no,
            ),
            "sell": ConditionPrices(
                token_id_yes=token_id_yes,
                token_id_no=token_id_no,
                price_yes=sell_yes,
                price_no=sell_no,
                outcome_yes=o_yes,
                outcome_no=o_no,
            ),
        }
