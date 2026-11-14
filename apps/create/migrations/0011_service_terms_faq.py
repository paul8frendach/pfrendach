from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("create", "0010_work_clip_work_still"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="terms",
            field=models.TextField(
                blank=True,
                help_text="The plain-English agreement — one term per line, as 'Title — detail'.",
            ),
        ),
        migrations.AddField(
            model_name="service",
            name="faq",
            field=models.TextField(
                blank=True,
                help_text="Common questions — one per line, as 'Question :: Answer'.",
            ),
        ),
    ]
