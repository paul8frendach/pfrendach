import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("create", "0006_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="commission",
            name="reference",
            field=models.CharField(
                blank=True, db_index=True, default="", max_length=12,
                help_text="Short code the client sees, e.g. OMV-7K2Q.",
            ),
        ),
        migrations.AddField(
            model_name="commission",
            name="client",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="omv_commissions",
                to=settings.AUTH_USER_MODEL,
                help_text="The client account this project belongs to, if they made one.",
            ),
        ),
        migrations.AddField(
            model_name="commission",
            name="quote_amount",
            field=models.DecimalField(
                blank=True, null=True, decimal_places=2, max_digits=9,
                help_text="The number quoted for the whole project.",
            ),
        ),
        migrations.AddField(
            model_name="commission",
            name="quote_deposit",
            field=models.DecimalField(
                blank=True, null=True, decimal_places=2, max_digits=9,
                help_text="Deposit that books the date. Blank falls back to the package deposit.",
            ),
        ),
        migrations.AddField(
            model_name="commission",
            name="quote_note",
            field=models.TextField(
                blank=True, help_text="A short message that rides with the quote.",
            ),
        ),
        migrations.AddField(
            model_name="commission",
            name="quoted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
