"""
FindThe90 Shop — local control layer over Printful.

PrintfulProduct: lets Alex control which Printful products appear on the
site, in what order, and with a custom name/description — without touching
Printful's dashboard for display choices.

PrintfulWebhookLog: append-only log of every webhook event Printful sends
(order status updates, etc.).
"""

from __future__ import annotations

from django.db import models
from django.utils.text import slugify

from apps.house.models import Published, TimeStamped


class PrintfulProduct(TimeStamped, Published):
    """
    Local override record for a Printful sync product.

    The sync_product_id is the Printful ID — used to call the API.
    Everything else is display control: the live flag, sort order, and
    optional name/description overrides.

    If display_name / display_description are blank, the shop falls back
    to the name/description returned by Printful.
    """

    sync_product_id = models.PositiveBigIntegerField(
        unique=True,
        help_text="Printful sync product ID (from the Printful dashboard).",
    )
    slug = models.SlugField(
        max_length=80,
        unique=True,
        help_text="URL slug for the product detail page.",
    )
    display_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Override Printful's product name for the storefront. Leave blank to use Printful's name.",
    )
    display_description = models.TextField(
        blank=True,
        help_text="Override product description shown on the site. Leave blank to use Printful's description.",
    )

    class Meta:
        ordering = ("sort", "display_name")
        verbose_name = "Printful product"
        verbose_name_plural = "Printful products"

    def __str__(self) -> str:
        return self.display_name or f"Printful #{self.sync_product_id}"

    def save(self, *args, **kwargs) -> None:
        if not self.slug and self.display_name:
            self.slug = slugify(self.display_name)
        super().save(*args, **kwargs)


class PrintfulWebhookLog(TimeStamped):
    """
    Append-only log of inbound Printful webhook events.

    Never delete rows — this is an audit trail. The status field is
    parsed from the event type so you can filter by it in the admin.
    """

    class EventType(models.TextChoices):
        ORDER_CREATED   = "order_created",   "Order created"
        ORDER_UPDATED   = "order_updated",   "Order updated"
        ORDER_FAILED    = "order_failed",    "Order failed"
        ORDER_CANCELED  = "order_canceled",  "Order canceled"
        PACKAGE_SHIPPED = "package_shipped", "Package shipped"
        PACKAGE_RETURNED = "package_returned", "Package returned"
        OTHER           = "other",           "Other / unknown"

    event_type  = models.CharField(
        max_length=30,
        choices=EventType.choices,
        default=EventType.OTHER,
        db_index=True,
    )
    printful_order_id = models.CharField(
        max_length=40,
        blank=True,
        db_index=True,
        help_text="Printful order ID extracted from the event payload.",
    )
    raw_payload = models.JSONField(
        help_text="Full JSON body received from Printful.",
    )
    # Did our handler process it successfully?
    processed = models.BooleanField(default=True)
    notes     = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Printful webhook log"
        verbose_name_plural = "Printful webhook logs"

    def __str__(self) -> str:
        return f"{self.event_type} · order {self.printful_order_id or '—'} · {self.created_at:%Y-%m-%d %H:%M}"
