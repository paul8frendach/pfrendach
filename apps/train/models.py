"""
FRENDACH — the Train world.

Doctrine is content. Sessions, slots and bookings are the storefront: a player
picks a session type, takes an open slot, and gets a reference back. Nothing is
confirmed until Paul confirms it.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from apps.house.models import Published, TimeStamped


def booking_reference() -> str:
    """Short, human-readable, non-sequential. Read aloud on a field without pain."""
    alphabet = "ACDEFHJKLMNPRTUVWXY349"
    return "FR-" + "".join(secrets.choice(alphabet) for _ in range(6))


class Law(TimeStamped, Published):
    """The Seven Laws. Numbered, because he numbers them."""

    number = models.PositiveSmallIntegerField(unique=True)
    title = models.CharField(max_length=60)
    body = models.TextField()

    class Meta:
        ordering = ("number",)

    def __str__(self) -> str:
        return f"{self.number}. {self.title}"


class SessionType(TimeStamped, Published):
    """A thing you can book. Price is optional — some of it is a conversation."""

    class Format(models.TextChoices):
        ONE_TO_ONE = "1v1", "One to one"
        SMALL_GROUP = "group", "Small group"
        FILM = "film", "Film session"
        BLOCK = "block", "Multi-week block"

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)
    format = models.CharField(max_length=10, choices=Format.choices, default=Format.ONE_TO_ONE)
    summary = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    focus = models.TextField(
        blank=True, help_text="One bullet per line. What the session actually works on."
    )
    duration_minutes = models.PositiveSmallIntegerField(default=60)
    capacity = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1)],
        help_text="Players per slot.",
    )
    price = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True,
        help_text="Leave blank to show the price note instead.",
    )
    price_note = models.CharField(max_length=80, blank=True, default="On request")
    requires_film = models.BooleanField(default=False)

    class Meta:
        ordering = ("sort", "name")

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("train:session_detail", args=[self.slug])

    @property
    def focus_points(self) -> list[str]:
        return [line.strip() for line in self.focus.splitlines() if line.strip()]

    @property
    def price_label(self) -> str:
        if self.price is None:
            return self.price_note or "On request"
        cents = self.price - int(self.price)
        return f"${int(self.price)}" if not cents else f"${self.price:.2f}"


class SlotQuerySet(models.QuerySet):
    def open(self):
        return (
            self.filter(status=Slot.Status.OPEN, starts_at__gte=timezone.now())
            .annotate(
                taken=Count(
                    "bookings",
                    filter=~Q(bookings__status__in=[Booking.Status.CANCELLED, Booking.Status.DECLINED]),
                )
            )
            .filter(taken__lt=models.F("capacity"))
        )

    def upcoming(self):
        return self.filter(starts_at__gte=timezone.now()).order_by("starts_at")


class Slot(TimeStamped):
    """A concrete window on the calendar. Capacity is copied from the session type."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        HELD = "held", "Held"
        CLOSED = "closed", "Closed"

    session_type = models.ForeignKey(
        SessionType, on_delete=models.CASCADE, related_name="slots"
    )
    starts_at = models.DateTimeField(db_index=True)
    location = models.CharField(max_length=120, default="Southern Maryland")
    capacity = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.OPEN)
    note = models.CharField(max_length=160, blank=True)

    objects = SlotQuerySet.as_manager()

    class Meta:
        ordering = ("starts_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("session_type", "starts_at"), name="unique_slot_per_session_start"
            )
        ]

    def __str__(self) -> str:
        return f"{self.session_type.name} · {timezone.localtime(self.starts_at):%a %d %b %H:%M}"

    def save(self, *args, **kwargs):
        if not self.pk and self.session_type_id and self.capacity == 1:
            self.capacity = self.session_type.capacity
        super().save(*args, **kwargs)

    @property
    def ends_at(self):
        return self.starts_at + timedelta(minutes=self.session_type.duration_minutes)

    @property
    def taken_count(self) -> int:
        return self.bookings.exclude(
            status__in=[Booking.Status.CANCELLED, Booking.Status.DECLINED]
        ).count()

    @property
    def seats_left(self) -> int:
        return max(self.capacity - self.taken_count, 0)

    @property
    def is_bookable(self) -> bool:
        return (
            self.status == self.Status.OPEN
            and self.starts_at >= timezone.now()
            and self.seats_left > 0
        )


class Booking(TimeStamped):
    """
    A request for a slot. Created as PENDING — confirmation is a human act,
    not a side effect of a form submit.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        DECLINED = "declined", "Declined"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    reference = models.CharField(
        max_length=12, unique=True, default=booking_reference, editable=False
    )
    slot = models.ForeignKey(Slot, on_delete=models.PROTECT, related_name="bookings")
    player_name = models.CharField(max_length=120)
    player_age = models.PositiveSmallIntegerField(null=True, blank=True)
    club_or_school = models.CharField(max_length=120, blank=True)
    position = models.CharField(max_length=60, blank=True)
    contact_name = models.CharField(
        max_length=120, blank=True, help_text="Parent or guardian, if the player is a minor."
    )
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    goal = models.TextField(blank=True, help_text="What they want out of the session.")
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    internal_note = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.reference} · {self.player_name}"

    def get_absolute_url(self) -> str:
        return reverse("train:booking_detail", args=[self.reference])

    @property
    def is_active(self) -> bool:
        return self.status in {self.Status.PENDING, self.Status.CONFIRMED}

    def confirm(self, *, save: bool = True) -> None:
        self.status = self.Status.CONFIRMED
        self.confirmed_at = timezone.now()
        if save:
            self.save(update_fields=["status", "confirmed_at", "updated_at"])
