"""
FindThe90 — Printful API v2 client.

Reads PRINTFUL_API_KEY from the environment (set in .env for local dev,
in the PA environment panel for production). All methods raise
PrintfulError on non-2xx responses so callers can catch cleanly.

Usage:
    from apps.shop.printful import PrintfulClient
    client = PrintfulClient()
    products = client.get_products()
"""

from __future__ import annotations

import logging
import os
from typing import Any

try:
    import requests
except ModuleNotFoundError:  # dev venv without the dep; the shop degrades gracefully
    requests = None

logger = logging.getLogger(__name__)

PRINTFUL_API_BASE = "https://api.printful.com"
TIMEOUT = 15  # seconds


class PrintfulError(Exception):
    """Raised on any non-2xx Printful API response."""

    def __init__(self, status: int, message: str) -> None:
        self.status = status
        self.message = message
        super().__init__(f"Printful {status}: {message}")


class PrintfulClient:
    """Thin wrapper around Printful API v2."""

    def __init__(self, api_key: str | None = None) -> None:
        self._key = api_key or os.environ.get("PRINTFUL_API_KEY", "")
        if not self._key:
            logger.warning(
                "PRINTFUL_API_KEY is not set — all Printful calls will fail."
            )

    # ---------------------------------------------------------------- internals

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
            "X-PF-Language": "en_US",
        }

    def _get(self, path: str, params: dict | None = None) -> Any:
        if requests is None:
            raise PrintfulError(0, "requests library is not installed")
        url = f"{PRINTFUL_API_BASE}{path}"
        try:
            resp = requests.get(url, headers=self._headers(), params=params, timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise PrintfulError(0, str(exc)) from exc
        return self._parse(resp)

    def _post(self, path: str, data: dict) -> Any:
        if requests is None:
            raise PrintfulError(0, "requests library is not installed")
        url = f"{PRINTFUL_API_BASE}{path}"
        try:
            resp = requests.post(url, headers=self._headers(), json=data, timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise PrintfulError(0, str(exc)) from exc
        return self._parse(resp)

    @staticmethod
    def _parse(resp: requests.Response) -> Any:
        try:
            body = resp.json()
        except ValueError:
            body = {}
        if not resp.ok:
            msg = body.get("error", {}).get("message", resp.text) if isinstance(body, dict) else resp.text
            raise PrintfulError(resp.status_code, msg)
        return body.get("result", body)

    # ---------------------------------------------------------------- products

    def get_products(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """
        Fetch the store's sync products.
        Returns a list of sync product objects.
        """
        result = self._get("/store/products", params={"limit": limit, "offset": offset})
        # Printful wraps paginated results in {"result": [...], "paging": {...}}
        if isinstance(result, dict) and "result" in result:
            return result["result"]
        return result if isinstance(result, list) else []

    def get_product(self, sync_product_id: int | str) -> dict:
        """
        Fetch a single sync product with its variants.
        Returns {"sync_product": {...}, "sync_variants": [...]}
        """
        return self._get(f"/store/products/{sync_product_id}")

    def get_variant(self, sync_variant_id: int | str) -> dict:
        """Fetch a single sync variant."""
        return self._get(f"/store/variants/{sync_variant_id}")

    # ---------------------------------------------------------------- orders

    def create_order(self, order_data: dict) -> dict:
        """
        Submit an order to Printful.

        Minimal order_data shape:
            {
                "recipient": {
                    "name": "Jane Player",
                    "address1": "123 Main St",
                    "city": "Frederick",
                    "state_code": "MD",
                    "country_code": "US",
                    "zip": "21701"
                },
                "items": [
                    {"sync_variant_id": 12345, "quantity": 1}
                ]
            }

        Returns the created order object.
        """
        return self._post("/orders", order_data)

    def get_order(self, order_id: int | str) -> dict:
        """Fetch an existing order by Printful order ID."""
        return self._get(f"/orders/{order_id}")
