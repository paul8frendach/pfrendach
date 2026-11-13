"""Initial migration for the shop app."""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PrintfulProduct",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_live", models.BooleanField(db_index=True, default=True)),
                ("sort", models.PositiveIntegerField(default=100, help_text="Low numbers first.")),
                ("sync_product_id", models.PositiveBigIntegerField(
                    help_text="Printful sync product ID (from the Printful dashboard).",
                    unique=True,
                )),
                ("slug", models.SlugField(
                    help_text="URL slug for the product detail page.",
                    max_length=80,
                    unique=True,
                )),
                ("display_name", models.CharField(
                    blank=True,
                    help_text="Override Printful's product name for the storefront. Leave blank to use Printful's name.",
                    max_length=200,
                )),
                ("display_description", models.TextField(
                    blank=True,
                    help_text="Override product description shown on the site. Leave blank to use Printful's description.",
                )),
            ],
            options={"ordering": ("sort", "display_name"), "verbose_name": "Printful product", "verbose_name_plural": "Printful products"},
        ),
        migrations.CreateModel(
            name="PrintfulWebhookLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("event_type", models.CharField(
                    choices=[
                        ("order_created", "Order created"),
                        ("order_updated", "Order updated"),
                        ("order_failed", "Order failed"),
                        ("order_canceled", "Order canceled"),
                        ("package_shipped", "Package shipped"),
                        ("package_returned", "Package returned"),
                        ("other", "Other / unknown"),
                    ],
                    db_index=True,
                    default="other",
                    max_length=30,
                )),
                ("printful_order_id", models.CharField(
                    blank=True,
                    db_index=True,
                    help_text="Printful order ID extracted from the event payload.",
                    max_length=40,
                )),
                ("raw_payload", models.JSONField(help_text="Full JSON body received from Printful.")),
                ("processed", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
            ],
            options={"ordering": ("-created_at",), "verbose_name": "Printful webhook log", "verbose_name_plural": "Printful webhook logs"},
        ),
    ]
