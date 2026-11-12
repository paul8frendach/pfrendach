import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("create", "0003_work_duration_seconds_work_height_work_source_path_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="work",
            name="category",
            field=models.CharField(
                choices=[
                    ("wedding", "Weddings"),
                    ("event", "Events"),
                    ("school", "Schools & Sports"),
                    ("listing", "Real estate & drone"),
                    ("brand", "Brand & business"),
                    ("stills", "Stills"),
                ],
                db_index=True,
                default="wedding",
                help_text="The market this piece belongs to. Drives the portfolio filter.",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="work",
            name="location",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Venue or town, e.g. Walker's Overlook · Walkersville, MD",
                max_length=120,
            ),
        ),
        migrations.CreateModel(
            name="Commission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("email", models.EmailField(max_length=254)),
                ("phone", models.CharField(blank=True, max_length=40)),
                (
                    "service",
                    models.CharField(
                        choices=[
                            ("wedding", "Wedding film"),
                            ("event", "Event film"),
                            ("school", "School / sports film"),
                            ("listing", "Listing film & drone"),
                            ("brand", "Brand / business film"),
                            ("other", "Something else"),
                        ],
                        db_index=True,
                        default="wedding",
                        max_length=10,
                    ),
                ),
                ("event_date", models.DateField(blank=True, help_text="If they have one.", null=True)),
                ("location", models.CharField(blank=True, help_text="Venue or town the shoot is in.", max_length=160)),
                ("details", models.TextField(help_text="What they are trying to make.")),
                ("budget", models.PositiveIntegerField(blank=True, help_text="Optional, in whole dollars.", null=True)),
                ("how_heard", models.CharField(blank=True, max_length=120)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "New"),
                            ("read", "Read"),
                            ("quoted", "Quoted"),
                            ("booked", "Booked"),
                            ("closed", "Closed"),
                        ],
                        db_index=True,
                        default="new",
                        max_length=10,
                    ),
                ),
                ("source_path", models.CharField(blank=True, max_length=200)),
                (
                    "notified_oasis",
                    models.BooleanField(
                        default=False,
                        help_text="Set once Oasis has picked this up as an enquiry, so it is not re-counted.",
                    ),
                ),
                (
                    "package",
                    models.ForeignKey(
                        blank=True,
                        help_text="If they started from a package, it is recorded here.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="commissions",
                        to="create.package",
                    ),
                ),
            ],
            options={
                "verbose_name": "commission request",
                "verbose_name_plural": "commission requests",
                "ordering": ("-created_at",),
            },
        ),
    ]
