import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("create", "0004_work_category_work_location_commission"),
    ]

    operations = [
        migrations.AddField(
            model_name="package",
            name="deposit_amount",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=8, null=True,
                help_text="Deposit that books the date. Set this to offer online booking for this package.",
            ),
        ),
        migrations.AddField(
            model_name="package",
            name="allow_online_booking",
            field=models.BooleanField(
                default=False,
                help_text="Show a Stripe 'Book — pay deposit' button (needs a deposit amount and Stripe keys).",
            ),
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("kind", models.CharField(
                    choices=[("deposit", "Deposit"), ("balance", "Balance"), ("full", "Full payment")],
                    default="deposit", max_length=10)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=9)),
                ("currency", models.CharField(default="usd", max_length=8)),
                ("description", models.CharField(blank=True, max_length=200)),
                ("customer_name", models.CharField(blank=True, max_length=160)),
                ("customer_email", models.EmailField(blank=True, max_length=254)),
                ("stripe_session_id", models.CharField(blank=True, db_index=True, max_length=120)),
                ("stripe_payment_intent", models.CharField(blank=True, db_index=True, max_length=120)),
                ("checkout_url", models.URLField(blank=True, max_length=600)),
                ("status", models.CharField(
                    choices=[("pending", "Pending"), ("paid", "Paid"), ("failed", "Failed"),
                             ("canceled", "Canceled"), ("refunded", "Refunded")],
                    db_index=True, default="pending", max_length=10)),
                ("source_path", models.CharField(blank=True, max_length=200)),
                ("notified_oasis", models.BooleanField(default=False)),
                ("commission", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="payments", to="create.commission")),
                ("package", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="payments", to="create.package")),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
