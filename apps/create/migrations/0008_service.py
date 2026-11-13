import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("create", "0007_commission_client_quote"),
    ]

    operations = [
        migrations.CreateModel(
            name="Service",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_live", models.BooleanField(db_index=True, default=True)),
                ("sort", models.PositiveIntegerField(default=100, help_text="Low numbers first.")),
                ("category", models.CharField(
                    choices=[("wedding", "Weddings"), ("event", "Events"), ("school", "Schools & Sports"),
                             ("listing", "Real estate & drone"), ("brand", "Brand & business"), ("stills", "Stills")],
                    db_index=True, max_length=10, unique=True)),
                ("slug", models.SlugField(max_length=60, unique=True)),
                ("title", models.CharField(max_length=80)),
                ("kicker", models.CharField(blank=True, max_length=60)),
                ("summary", models.CharField(help_text="The one-line context.", max_length=220)),
                ("body", models.TextField(blank=True, help_text="What this service actually is.")),
                ("includes", models.TextField(blank=True, help_text="One deliverable per line.")),
                ("process", models.TextField(blank=True, help_text="One step per line, as 'Title — detail'.")),
                ("clip", models.CharField(blank=True, help_text="Video filename under static/omv/service/.", max_length=120)),
                ("poster", models.CharField(blank=True, help_text="Poster image under static/omv/service/.", max_length=120)),
            ],
            options={"ordering": ("sort", "title")},
        ),
    ]
