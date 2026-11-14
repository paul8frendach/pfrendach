import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("create", "0008_service"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectLike",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("commission", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="likes", to="create.commission")),
                ("photo", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="likes", to="create.photo")),
            ],
            options={"ordering": ("-created_at",), "unique_together": {("commission", "photo")}},
        ),
    ]
