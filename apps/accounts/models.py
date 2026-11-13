"""
Accounts — player profiles, coach offers, messaging, and notifications.

PlayerProfile extends the built-in User with a coach-assigned rating.
Offer is a piece of marketing content targeted by rating tier.
Thread / Message / Notification power the in-app messaging system.
"""

from __future__ import annotations

import secrets
import string

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from apps.house.models import Published, TimeStamped


# ---------------------------------------------------------------- player profile

class PlayerProfile(TimeStamped):
    """
    One-to-one extension of Django's User.
    Created on signup; the coach assigns ratings and notes later.
    """

    class Rating(models.IntegerChoices):
        UNRATED    = 0, "Unrated"
        DEVELOPING = 1, "Developing"
        IMPROVING  = 2, "Improving"
        SOLID      = 3, "Solid"
        STRONG     = 4, "Strong"
        ELITE      = 5, "Elite"

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )
    rating = models.PositiveSmallIntegerField(
        choices=Rating.choices,
        default=Rating.UNRATED,
        db_index=True,
        help_text="Coach-assigned development rating. Players cannot edit this.",
    )
    rating_set_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the coach last updated this rating.",
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal coaching notes — never shown to the player.",
    )
    club     = models.CharField(max_length=80, blank=True)
    position = models.CharField(max_length=60, blank=True)
    grad_year = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Graduation year (helps gauge age group).",
    )

    class Meta:
        ordering = ("-rating", "user__last_name")
        verbose_name = "player profile"
        verbose_name_plural = "player profiles"

    def __str__(self) -> str:
        name = self.user.get_full_name() or self.user.username
        return f"{name} — {self.get_rating_display()}"

    @property
    def display_name(self) -> str:
        return self.user.get_full_name() or self.user.username

    @property
    def is_rated(self) -> bool:
        return self.rating > 0

    def set_rating(self, rating: int, *, save: bool = True) -> None:
        self.rating = rating
        self.rating_set_at = timezone.now()
        if save:
            self.save(update_fields=["rating", "rating_set_at", "updated_at"])


# ---------------------------------------------------------------- offers

class Offer(TimeStamped, Published):
    """
    Marketing content targeted by player rating tier.
    min_rating=0 / max_rating=5 = visible to everyone (with auth check).
    """

    title      = models.CharField(max_length=120)
    body       = models.TextField(
        help_text="Shown to eligible players. Keep it short and direct.",
    )
    cta_label  = models.CharField(max_length=40, default="Book a session")
    cta_url    = models.CharField(
        max_length=200, blank=True,
        help_text="Relative path (e.g. /train/enquire/) or absolute URL.",
    )
    min_rating = models.PositiveSmallIntegerField(
        choices=PlayerProfile.Rating.choices,
        default=0,
        help_text="Minimum player rating (0 = all players).",
    )
    max_rating = models.PositiveSmallIntegerField(
        choices=PlayerProfile.Rating.choices,
        default=5,
        help_text="Maximum player rating (5 = all players).",
    )
    requires_auth = models.BooleanField(
        default=True,
        help_text="Only logged-in players see this offer.",
    )
    tier_label = models.CharField(
        max_length=40, blank=True,
        help_text="Shown on the offer card (e.g. 'Elite players').",
    )

    class Meta:
        ordering = ("sort", "min_rating", "title")

    def __str__(self) -> str:
        return f"{self.title} [{self.tier_label}]" if self.tier_label else self.title

    def is_visible_to(self, user) -> bool:
        if not self.is_live:
            return False
        if self.requires_auth and (not user or not user.is_authenticated):
            return False
        if not user or not user.is_authenticated:
            return self.min_rating == 0
        try:
            rating = user.profile.rating
        except PlayerProfile.DoesNotExist:
            rating = 0
        return self.min_rating <= rating <= self.max_rating


# ---------------------------------------------------------------- messaging

def thread_ref() -> str:
    """Short human-readable thread reference: FT-XXXX."""
    chars = string.ascii_uppercase + string.digits
    return "FT-" + "".join(secrets.choice(chars) for _ in range(6))


class Thread(TimeStamped):
    """
    A conversation between a player and Alex.
    Optionally linked to a training service for context.
    """

    class Status(models.TextChoices):
        OPEN       = "open",       "Open"
        WAITING    = "waiting",    "Waiting on player"
        ESCALATED  = "escalated",  "Needs Alex"
        CLOSED     = "closed",     "Closed"

    reference   = models.CharField(
        max_length=12, unique=True, default=thread_ref, editable=False,
    )
    player      = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="threads",
    )
    subject     = models.CharField(max_length=200, default="Training enquiry")
    status      = models.CharField(
        max_length=12, choices=Status.choices, default=Status.OPEN, db_index=True,
    )
    # Optional: which service prompted this thread
    service_slug = models.CharField(
        max_length=80, blank=True,
        help_text="Slug of the training service this thread is about.",
    )
    service_name = models.CharField(max_length=120, blank=True)
    # Has the coach seen the latest message?
    coach_unread = models.BooleanField(default=True, db_index=True)
    # Has the player seen the latest reply?
    player_unread = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ("-updated_at",)

    def __str__(self) -> str:
        name = self.player.get_full_name() or self.player.username
        return f"{self.reference} · {name} · {self.subject}"

    @property
    def last_message(self):
        return self.messages.order_by("-created_at").first()

    @property
    def message_count(self) -> int:
        return self.messages.count()

    def mark_coach_read(self) -> None:
        if self.coach_unread:
            self.coach_unread = False
            self.save(update_fields=["coach_unread"])

    def mark_player_read(self) -> None:
        if self.player_unread:
            self.player_unread = False
            self.save(update_fields=["player_unread"])


class Message(TimeStamped):
    """
    A single message in a thread.
    is_ai_response=True means the AI layer generated it; Alex reviews/escalates.
    """

    class SenderType(models.TextChoices):
        PLAYER = "player", "Player"
        COACH  = "coach",  "Coach"
        AI     = "ai",     "AI assistant"

    thread       = models.ForeignKey(
        Thread, on_delete=models.CASCADE, related_name="messages",
    )
    sender_type  = models.CharField(
        max_length=8, choices=SenderType.choices,
    )
    sender       = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sent_messages",
        help_text="Null for AI-generated messages.",
    )
    body         = models.TextField()
    is_ai_response = models.BooleanField(
        default=False,
        help_text="True when this message was generated by the AI layer.",
    )
    # Escalated = AI flagged this for Alex's personal reply
    is_escalation = models.BooleanField(
        default=False,
        help_text="AI decided this needs Alex to respond directly.",
    )
    is_read_by_coach  = models.BooleanField(default=False, db_index=True)
    is_read_by_player = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"[{self.sender_type}] {self.body[:60]}"


class Notification(TimeStamped):
    """
    In-app notification badge. Created by the messaging layer; cleared on read.
    """

    class Kind(models.TextChoices):
        NEW_MESSAGE  = "message",  "New message"
        REPLY        = "reply",    "Reply from Alex"
        ESCALATION   = "escalate", "Needs attention"
        OFFER        = "offer",    "New offer available"

    user    = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications",
    )
    kind    = models.CharField(max_length=10, choices=Kind.choices)
    title   = models.CharField(max_length=120)
    body    = models.CharField(max_length=200, blank=True)
    url     = models.CharField(max_length=200, blank=True)
    thread  = models.ForeignKey(
        Thread, on_delete=models.CASCADE, null=True, blank=True,
        related_name="notifications",
    )
    is_read = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.user.username} · {self.kind} · {'read' if self.is_read else 'unread'}"

    def mark_read(self) -> None:
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=["is_read"])
