"""
Add choices to Offer.min_rating and Offer.max_rating so that
get_min_rating_display() / get_max_rating_display() work correctly.

Choices are metadata only — SQLite does not store them, so this migration
makes no structural change to the database.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="offer",
            name="min_rating",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, "Unrated"),
                    (1, "Developing"),
                    (2, "Improving"),
                    (3, "Solid"),
                    (4, "Strong"),
                    (5, "Elite"),
                ],
                default=0,
                help_text="Minimum player rating (0 = all players).",
            ),
        ),
        migrations.AlterField(
            model_name="offer",
            name="max_rating",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, "Unrated"),
                    (1, "Developing"),
                    (2, "Improving"),
                    (3, "Solid"),
                    (4, "Strong"),
                    (5, "Elite"),
                ],
                default=5,
                help_text="Maximum player rating (5 = all players).",
            ),
        ),
    ]
