from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("create", "0009_projectlike"),
    ]

    operations = [
        migrations.AddField(
            model_name="work",
            name="clip",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Committed web clip under static/omv/reel/, e.g. autumn.mp4. "
                    "Ships with the site and is preferred over video_file, so the "
                    "host needs no media server."
                ),
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name="work",
            name="still",
            field=models.CharField(
                blank=True,
                help_text="Committed poster under static/omv/reel/, e.g. autumn.jpg.",
                max_length=200,
            ),
        ),
    ]
