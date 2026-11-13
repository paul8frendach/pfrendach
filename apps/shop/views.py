"""
FindThe90 Shop views.

Product data is fetched from Printful and cached for PRINTFUL_CACHE_SECONDS
(default 15 min) to avoid hammering the API. The local PrintfulProduct table
acts as an allow-list and display override: only products with a matching
PrintfulProduct row (and is_live=True) appear on the site.

Webhook view accepts inbound Printful POST events and logs them.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os

from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import PrintfulProduct, PrintfulWebhookLog
from .printful import PrintfulClient, PrintfulError

logger = logging.getLogger(__name__)

CACHE_SECONDS = int(os.environ.get("PRINTFUL_CACHE_SECONDS", "900"))  # 15 min


# ---------------------------------------------------------------- helpers

def _get_client() -> PrintfulClient:
    return PrintfulClient()


def _fetch_product_detail(sync_product_id: int) -> dict | None:
    """Fetch a single product from Printful (or cache)."""
    key = f"pf_product_{sync_product_id}"
    data = cache.get(key)
    if data is None:
        try:
            data = _get_client().get_product(sync_product_id)
            cache.set(key, data, CACHE_SECONDS)
        except PrintfulError as exc:
            logger.error("Printful get_product(%s) failed: %s", sync_product_id, exc)
            return None
    return data


def _fetch_all_products() -> dict[int, dict]:
    """
    Fetch all Printful products indexed by sync_product_id.
    Returns {} on API error so the page degrades gracefully.
    """
    key = "pf_products_all"
    data = cache.get(key)
    if data is None:
        try:
            items = _get_client().get_products()
            data = {int(p["id"]): p for p in items}
            cache.set(key, data, CACHE_SECONDS)
        except PrintfulError as exc:
            logger.error("Printful get_products() failed: %s", exc)
            data = {}
    return data


# ---------------------------------------------------------------- public views

def product_list(request: HttpRequest) -> HttpResponse:
    """
    /shop/ — show all active Printful products in display_order.
    """
    local_products = (
        PrintfulProduct.objects.filter(is_live=True)
        .order_by("sort", "display_name")
    )

    pf_data = _fetch_all_products()

    products = []
    for local in local_products:
        pf = pf_data.get(local.sync_product_id, {})
        thumbnail = (
            pf.get("thumbnail_url")
            or (pf.get("sync_product") or {}).get("thumbnail_url", "")
        )
        products.append(
            {
                "local": local,
                "name": local.display_name or pf.get("name", f"Product #{local.sync_product_id}"),
                "thumbnail": thumbnail,
                "pf": pf,
            }
        )

    return render(
        request,
        "shop/product_list.html",
        {"products": products},
    )


def product_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """
    /shop/<slug>/ — show a single product with its variants.
    """
    local = get_object_or_404(PrintfulProduct, slug=slug, is_live=True)
    pf = _fetch_product_detail(local.sync_product_id) or {}

    sync_product = pf.get("sync_product", {})
    sync_variants = pf.get("sync_variants", [])

    return render(
        request,
        "shop/product_detail.html",
        {
            "local": local,
            "name": local.display_name or sync_product.get("name", ""),
            "description": local.display_description or sync_product.get("description", ""),
            "thumbnail": sync_product.get("thumbnail_url", ""),
            "variants": sync_variants,
            "pf": pf,
        },
    )


# ---------------------------------------------------------------- webhook

@csrf_exempt
@require_POST
def printful_webhook(request: HttpRequest) -> JsonResponse:
    """
    POST /shop/printful/webhook/

    Printful sends order status events here. We log every event to
    PrintfulWebhookLog for the audit trail. No signature verification
    is enforced by default (Printful v2 supports an optional secret);
    add PRINTFUL_WEBHOOK_SECRET to .env when you're ready to lock it down.
    """
    secret = os.environ.get("PRINTFUL_WEBHOOK_SECRET", "")
    if secret:
        signature = request.headers.get("X-PF-Signature", "")
        expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            logger.warning("Printful webhook: bad signature")
            return JsonResponse({"ok": False, "error": "bad signature"}, status=403)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        logger.warning("Printful webhook: invalid JSON")
        return JsonResponse({"ok": False, "error": "invalid JSON"}, status=400)

    event_type_raw = payload.get("type", "")

    # Map Printful event type string to our choice
    type_map = {
        "order_created":    PrintfulWebhookLog.EventType.ORDER_CREATED,
        "order_updated":    PrintfulWebhookLog.EventType.ORDER_UPDATED,
        "order_failed":     PrintfulWebhookLog.EventType.ORDER_FAILED,
        "order_canceled":   PrintfulWebhookLog.EventType.ORDER_CANCELED,
        "package_shipped":  PrintfulWebhookLog.EventType.PACKAGE_SHIPPED,
        "package_returned": PrintfulWebhookLog.EventType.PACKAGE_RETURNED,
    }
    event_type = type_map.get(event_type_raw, PrintfulWebhookLog.EventType.OTHER)

    order_id = ""
    data = payload.get("data", {})
    if isinstance(data, dict):
        order = data.get("order", {}) or {}
        order_id = str(order.get("id", ""))

    try:
        PrintfulWebhookLog.objects.create(
            event_type=event_type,
            printful_order_id=order_id,
            raw_payload=payload,
            processed=True,
        )
    except Exception as exc:
        logger.error("Failed to save PrintfulWebhookLog: %s", exc)
        return JsonResponse({"ok": False, "error": "storage error"}, status=500)

    logger.info("Printful webhook: %s · order %s", event_type_raw, order_id or "—")
    return JsonResponse({"ok": True})
