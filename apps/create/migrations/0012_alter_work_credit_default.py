from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("create", "0011_service_terms_faq"),
    ]

    operations = [
        migrations.AlterField(
            model_name="work",
            name="credit",
            field=models.CharField(default="Oasis Media Visions", max_length=120),
        ),
    ]
