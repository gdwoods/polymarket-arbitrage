"""
Execution client for placing arbitrage trades on Polymarket.

Uses py-clob-client to submit buy/sell orders. Requires wallet setup and API credentials.
"""

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..arbitrage.single_condition import ArbitrageOpportunity


@dataclass
class ExecutionResult:
    success: bool
    order_ids: list[str]
    message: str
    dry_run: bool


class ExecutionClient:
    def __init__(
        self,
        private_key: str,
        funder: str,
        signature_type: int = 1,
        chain_id: int = 137,
        host: str = "https://clob.polymarket.com",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        api_passphrase: Optional[str] = None,
    ):
        self.private_key = private_key
        self.funder = funder
        self.signature_type = signature_type
        self.chain_id = chain_id
        self.host = host
        self._api_key = api_key
        self._api_secret = api_secret
        self._api_passphrase = api_passphrase
        self._client = None

    @classmethod
    def from_env(cls) -> "ExecutionClient":
        key = os.environ.get("POLYMARKET_PRIVATE_KEY")
        funder = os.environ.get("POLYMARKET_FUNDER")
        if not key or not funder:
            raise ValueError("Set POLYMARKET_PRIVATE_KEY and POLYMARKET_FUNDER in environment")
        sig_type = int(os.environ.get("POLYMARKET_SIGNATURE_TYPE", "1"))
        return cls(
            private_key=key,
            funder=funder,
            signature_type=sig_type,
            api_key=os.environ.get("POLYMARKET_API_KEY"),
            api_secret=os.environ.get("POLYMARKET_API_SECRET"),
            api_passphrase=os.environ.get("POLYMARKET_API_PASSPHRASE"),
        )

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from py_clob_client.client import ClobClient
        except ImportError:
            raise ImportError("pip install py-clob-client")
        client = ClobClient(
            self.host,
            chain_id=self.chain_id,
            key=self.private_key,
            signature_type=self.signature_type,
            funder=self.funder,
        )
        if self._api_key and self._api_secret and self._api_passphrase:
            from py_clob_client.clob_types import ApiCreds
            creds = ApiCreds(
                api_key=self._api_key,
                api_secret=self._api_secret,
                api_passphrase=self._api_passphrase,
            )
            client.set_api_creds(creds)
        else:
            client.set_api_creds(client.create_or_derive_api_creds())
        self._client = client
        return self._client

    def execute_buy_both(
        self,
        opportunity: "ArbitrageOpportunity",
        size: float,
        dry_run: bool = True,
    ) -> ExecutionResult:
        if opportunity.direction != "buy_both":
            return ExecutionResult(success=False, order_ids=[], message=f"Opportunity is {opportunity.direction}, not buy_both", dry_run=dry_run)
        if dry_run:
            cost = opportunity.price_yes * size + opportunity.price_no * size
            profit = size - cost
            return ExecutionResult(
                success=True,
                order_ids=[],
                message=f"[DRY RUN] Would buy {size} YES @ {opportunity.price_yes:.4f} and {size} NO @ {opportunity.price_no:.4f}. Cost ${cost:.2f}, profit ${profit:.2f}",
                dry_run=True,
            )
        return self._place_buy_both_orders(opportunity, size)

    def execute_sell_both(
        self,
        opportunity: "ArbitrageOpportunity",
        size: float,
        dry_run: bool = True,
    ) -> ExecutionResult:
        if opportunity.direction != "sell_both":
            return ExecutionResult(success=False, order_ids=[], message=f"Opportunity is {opportunity.direction}, not sell_both", dry_run=dry_run)
        if dry_run:
            revenue = opportunity.price_yes * size + opportunity.price_no * size
            profit = revenue - size
            return ExecutionResult(
                success=True,
                order_ids=[],
                message=f"[DRY RUN] Would sell {size} YES @ {opportunity.price_yes:.4f} and {size} NO @ {opportunity.price_no:.4f}. Revenue ${revenue:.2f}, profit ${profit:.2f}",
                dry_run=True,
            )
        return self._place_sell_both_orders(opportunity, size)

    def _place_buy_both_orders(self, opportunity: "ArbitrageOpportunity", size: float) -> ExecutionResult:
        from py_clob_client.clob_types import OrderArgs
        client = self._get_client()
        order_ids = []
        try:
            for token_id, price, side in [
                (opportunity.token_id_yes, opportunity.price_yes, "BUY"),
                (opportunity.token_id_no, opportunity.price_no, "BUY"),
            ]:
                order_args = OrderArgs(token_id=token_id, price=price, size=size, side=side)
                resp = client.create_and_post_order(order_args)
                oid = resp.get("orderID", resp.get("order_id")) if isinstance(resp, dict) else getattr(resp, "orderID", getattr(resp, "order_id", None))
                if oid:
                    order_ids.append(str(oid))
        except Exception as e:
            return ExecutionResult(success=False, order_ids=order_ids, message=str(e), dry_run=False)
        return ExecutionResult(success=True, order_ids=order_ids, message=f"Placed {len(order_ids)} orders", dry_run=False)

    def _place_sell_both_orders(self, opportunity: "ArbitrageOpportunity", size: float) -> ExecutionResult:
        from py_clob_client.clob_types import OrderArgs
        client = self._get_client()
        order_ids = []
        try:
            for token_id, price, side in [
                (opportunity.token_id_yes, opportunity.price_yes, "SELL"),
                (opportunity.token_id_no, opportunity.price_no, "SELL"),
            ]:
                order_args = OrderArgs(token_id=token_id, price=price, size=size, side=side)
                resp = client.create_and_post_order(order_args)
                oid = resp.get("orderID", resp.get("order_id")) if isinstance(resp, dict) else getattr(resp, "orderID", getattr(resp, "order_id", None))
                if oid:
                    order_ids.append(str(oid))
        except Exception as e:
            return ExecutionResult(success=False, order_ids=order_ids, message=str(e), dry_run=False)
        return ExecutionResult(success=True, order_ids=order_ids, message=f"Placed {len(order_ids)} sell orders", dry_run=False)