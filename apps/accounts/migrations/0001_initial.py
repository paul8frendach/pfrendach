"""
Initial migration for the accounts app.
Creates: PlayerProfile, Offer, Thread, Message, Notification.
"""

import apps.accounts.models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ---------------------------------------------------------------- PlayerProfile
        migrations.CreateModel(
            name="PlayerProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "rating",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "Unrated"),
                            (1, "Developing"),
                            (2, "Improving"),
                            (3, "Solid"),
                            (4, "Strong"),
                            (5, "Elite"),
                        ],
                        db_index=True,
                        default=0,
                        help_text="Coach-assigned development rating. Players cannot edit this.",
                    ),
                ),
                (
                    "rating_set_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        help_text="When the coach last updated this rating.",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="Internal coaching notes — never shown to the player.",
                    ),
                ),
                ("club",      models.CharField(blank=True, max_length=80)),
                ("position",  models.CharField(blank=True, max_length=60)),
                (
                    "grad_year",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        help_text="Graduation year (helps gauge age group).",
                    ),
                ),
            ],
            options={
                "verbose_name": "player profile",
                "verbose_name_plural": "player profiles",
                "ordering": ("-rating", "user__last_name"),
            },
        ),

        # ---------------------------------------------------------------- Offer
        migrations.CreateModel(
            name="Offer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_live", models.BooleanField(db_index=True, default=True)),
                ("sort",    models.PositiveIntegerField(default=100, help_text="Low numbers first.")),
                ("title",   models.CharField(max_length=120)),
                (
                    "body",
                    models.TextField(help_text="Shown to eligible players. Keep it short and direct."),
                ),
                ("cta_label", models.CharField(default="Book a session", max_length=40)),
                (
                    "cta_url",
                    models.CharField(
                        blank=True,
                        max_length=200,
                        help_text="Relative path (e.g. /train/enquire/) or absolute URL.",
                    ),
                ),
                (
                    "min_rating",
                    models.PositiveSmallIntegerField(
                        default=0,
                        help_text="Minimum player rating (0 = all players).",
                    ),
                ),
                (
                    "max_rating",
                    models.PositiveSmallIntegerField(
                        default=5,
                        help_text="Maximum player rating (5 = all players).",
                    ),
                ),
                (
                    "requires_auth",
                    models.BooleanField(
                        default=True,
                        help_text="Only logged-in players see this offer.",
                    ),
                ),
                (
                    "tier_label",
                    models.CharField(
                        blank=True,
                        max_length=40,
                        help_text="Shown on the offer card (e.g. 'Elite players').",
                    ),
                ),
            ],
            options={
                "ordering": ("sort", "min_rating", "title"),
            },
        ),

        # ---------------------------------------------------------------- Thread
        migrations.CreateModel(
            name="Thread",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "reference",
                    models.CharField(
                        default=apps.accounts.models.thread_ref,
                        editable=False,
                        max_length=12,
                        unique=True,
                    ),
                ),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="threads",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("subject", models.CharField(default="Training enquiry", max_length=200)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open",      "Open"),
                            ("waiting",   "Waiting on player"),
                            ("escalated", "Needs Alex"),
                            ("closed",    "Closed"),
                        ],
                        db_index=True,
                        default="open",
                        max_length=12,
                    ),
                ),
                (
                    "service_slug",
                    models.CharField(
                        blank=True,
                        max_length=80,
                        help_text="Slug of the training service this thread is about.",
                    ),
                ),
                ("service_name",  models.CharField(blank=True, max_length=120)),
                ("coach_unread",  models.BooleanField(db_index=True, default=True)),
                ("player_unread", models.BooleanField(db_index=True, default=False)),
            ],
            options={
                "ordering": ("-updated_at",),
            },
        ),

        # ---------------------------------------------------------------- Message
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "thread",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="accounts.thread",
                    ),
                ),
                (
                    "sender_type",
                    models.CharField(
                        choices=[
                            ("player", "Player"),
                            ("coach",  "Coach"),
                            ("ai",     "AI assistant"),
                        ],
                        max_length=8,
                    ),
                ),
                (
                    "sender",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sent_messages",
                        to=settings.AUTH_USER_MODEL,
                        help_text="Null for AI-generated messages.",
                    ),
                ),
                ("body", models.TextField()),
                (
                    "is_ai_response",
                    models.BooleanField(
                        default=False,
                        help_text="True when this message was generated by the AI layer.",
                    ),
                ),
                (
                    "is_escalation",
                    models.BooleanField(
                        default=False,
                        help_text="AI decided this needs Alex to respond directly.",
                    ),
                ),
                ("is_read_by_coach",  models.BooleanField(db_index=True, default=False)),
                ("is_read_by_player", models.BooleanField(db_index=True, default=False)),
            ],
            options={
                "ordering": ("created_at",),
            },
        ),

        # ---------------------------------------------------------------- Notification
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("message",  "New message"),
                            ("reply",    "Reply from Alex"),
                            ("escalate", "Needs attention"),
                            ("offer",    "New offer available"),
                        ],
                        max_length=10,
                    ),
                ),
                ("title",   models.CharField(max_length=120)),
                ("body",    models.CharField(blank=True, max_length=200)),
                ("url",     models.CharField(blank=True, max_length=200)),
                (
                    "thread",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to="accounts.thread",
                    ),
                ),
                ("is_read", models.BooleanField(db_index=True, default=False)),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
    ]
