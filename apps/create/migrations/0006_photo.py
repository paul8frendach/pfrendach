import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("create", "0005_package_deposit_payment"),
    ]

    operations = [
        migrations.CreateModel(
            name="Photo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_live", models.BooleanField(db_index=True, default=True)),
                ("sort", models.PositiveIntegerField(default=100, help_text="Low numbers first.")),
                ("image", models.CharField(help_text="Filename under static/omv/gallery/", max_length=200)),
                ("style", models.CharField(
                    choices=[("wedding", "Weddings & couples"), ("portrait", "Portraits & graduation"),
                             ("sports", "Sports"), ("aerial", "Aerial & drone"), ("event", "Events")],
                    db_index=True, default="wedding", max_length=10)),
                ("title", models.CharField(blank=True, max_length=140)),
                ("caption", models.CharField(blank=True, max_length=200)),
                ("width", models.PositiveIntegerField(blank=True, null=True)),
                ("height", models.PositiveIntegerField(blank=True, null=True)),
                ("is_featured", models.BooleanField(default=False)),
            ],
            options={"ordering": ("style", "sort", "-created_at")},
        ),
    ]
