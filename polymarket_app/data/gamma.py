"""Gamma API client for Polymarket market discovery."""

import json
import httpx
from typing import Any

from ..config import GAMMA_API
from .models import Market


def _parse_json_field(val: Any) -> Any:
    """Parse JSON string fields from Gamma API (e.g. outcomes, outcomePrices)."""
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return val
    return val


class GammaClient:
    """Client for Polymarket Gamma API - market discovery and metadata."""

    def __init__(self, base_url: str = GAMMA_API):
        self.base_url = base_url.rstrip("/")

    async def get_events(
        self,
        active: bool = True,
        closed: bool = False,
        limit: int = 50,
        offset: int = 0,
        tag_id: str | None = None,
        end_date_min: str | None = None,
        end_date_max: str | None = None,
    ) -> list[dict]:
        """Fetch active events.
        end_date_min/end_date_max: ISO datetime strings to filter by resolution date.
        """
        params: dict[str, Any] = {
            "active": str(active).lower(),
            "closed": str(closed).lower(),
            "limit": limit,
            "offset": offset,
        }
        if tag_id:
            params["tag_id"] = tag_id
        if end_date_min:
            params["end_date_min"] = end_date_min
        if end_date_max:
            params["end_date_max"] = end_date_max
        timeout = httpx.Timeout(60.0)  # Gamma can be slow with large payloads
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(f"{self.base_url}/events", params=params)
            r.raise_for_status()
            return r.json()

    async def get_markets(
        self,
        closed: bool = False,
        limit: int = 100,
        offset: int = 0,
        slug: str | None = None,
    ) -> list[dict]:
        """Fetch markets."""
        params: dict[str, Any] = {
            "closed": str(closed).lower(),
            "limit": limit,
            "offset": offset,
        }
        if slug:
            params["slug"] = slug
        timeout = httpx.Timeout(60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(f"{self.base_url}/markets", params=params)
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else [data]

    def _event_to_markets(self, event: dict) -> list[Market]:
        """Convert event payload to Market objects."""
        markets = []
        for m in event.get("markets", []):
            markets.append(self._raw_to_market(m, event))
        return markets

    def _raw_to_market(self, raw: dict, event: dict | None = None) -> Market:
        """Convert raw market dict to Market model."""
        outcomes = _parse_json_field(raw.get("outcomes", ["Yes", "No"]))
        outcome_prices = _parse_json_field(raw.get("outcomePrices", ["0.5", "0.5"]))
        clob_token_ids = raw.get("clobTokenIds") or raw.get("clob_token_ids") or raw.get("condition_id", "")
        clob_token_ids = _parse_json_field(clob_token_ids)
        if isinstance(clob_token_ids, str):
            clob_token_ids = [clob_token_ids] if clob_token_ids else []

        event_slug = event.get("slug", "") if event else ""
        market_slug = raw.get("slug", event_slug)
        end_date = (
            raw.get("endDate") or raw.get("end_date") or raw.get("endDateIso") or ""
        )
        if not end_date and event:
            end_date = event.get("endDate") or event.get("end_date") or ""
        return Market(
            id=raw.get("id", raw.get("conditionId", "")),
            question=raw.get("question", ""),
            slug=market_slug,
            event_slug=event_slug,
            condition_id=raw.get("conditionId", raw.get("condition_id", raw.get("id", ""))),
            end_date=end_date if isinstance(end_date, str) else str(end_date or ""),
            outcomes=outcomes if isinstance(outcomes, list) else ["Yes", "No"],
            outcome_prices=[float(p) for p in outcome_prices] if isinstance(outcome_prices, list) else [0.5, 0.5],
            clob_token_ids=clob_token_ids,
        )

    async def fetch_active_markets(
        self,
        limit: int = 100,
        end_date_min: str | None = None,
        end_date_max: str | None = None,
    ) -> list[Market]:
        """Fetch active markets from events (most efficient per docs).
        end_date_min/end_date_max: Filter by resolution date (ISO, e.g. '2025-01-01', '2026-12-31T23:59:59Z').
        """
        events = await self.get_events(
            active=True,
            closed=False,
            limit=limit,
            end_date_min=end_date_min,
            end_date_max=end_date_max,
        )
        markets: list[Market] = []
        for e in events:
            markets.extend(self._event_to_markets(e))
        return markets
