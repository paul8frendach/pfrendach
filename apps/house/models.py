"""House-level models: the person, the worlds, and anything that reaches him."""

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class TimeStamped(models.Model):
    """Every record in the house knows when it arrived and when it last moved."""

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Published(models.Model):
    """Sort order + a live switch, so nothing ships before he says so."""

    is_live = models.BooleanField(default=True, db_index=True)
    sort = models.PositiveIntegerField(default=100, help_text="Low numbers first.")

    class Meta:
        abstract = True


class SiteConfig(TimeStamped):
    """Singleton. Edited in admin, read everywhere through the context processor."""

    kicker = models.CharField(max_length=120, default="Create · Build · Train")
    headline = models.CharField(max_length=200, default="One house. Three rooms.")
    lead = models.TextField(
        default=(
            "Paul Frendach. Maryland. Films, interfaces, and sessions made by one "
            "pair of hands."
        )
    )
    contact_email = models.EmailField(default="hello@paulfrendach.com")
    location = models.CharField(max_length=120, default="Maryland")
    footer_line = models.CharField(max_length=200, default="Love the process.")
    booking_note = models.CharField(
        max_length=200,
        blank=True,
        default="Small roster. High school first. Few clients, full attention.",
    )
    instagram_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    show_intro_sting = models.BooleanField(
        default=True, help_text="Play the 10s sting in the home hero."
    )

    class Meta:
        verbose_name = "site configuration"
        verbose_name_plural = "site configuration"

    def __str__(self) -> str:
        return "Site configuration"

    def save(self, *args, **kwargs):
        # Always row 1. Drop force_insert so `objects.create()` on an existing
        # config updates it rather than colliding on the primary key.
        self.pk = 1
        kwargs.pop("force_insert", None)
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "SiteConfig":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class World(TimeStamped, Published):
    """
    Create / Build / Train. A world changes --accent, copy and imagery.
    It never changes the house mark.
    """

    class Slug(models.TextChoices):
        CREATE = "create", "Create — Vision Oasis"
        BUILD = "build", "Build — Web"
        TRAIN = "train", "Train — FRENDACH"

    slug = models.SlugField(max_length=16, unique=True, choices=Slug.choices)
    name = models.CharField(max_length=60, help_text="Vision Oasis / Web / FRENDACH")
    verb = models.CharField(max_length=20, help_text="Create / Build / Train")
    descriptor = models.CharField(max_length=80, help_text="Content & Cinema, Soccer Training…")
    kicker = models.CharField(max_length=120, blank=True)
    headline = models.CharField(max_length=200)
    lead = models.TextField()
    card_line = models.CharField(
        max_length=160, help_text="One line on the home page card."
    )
    cta_label = models.CharField(max_length=40, default="Enter")
    hero_image = models.ImageField(upload_to="worlds/", blank=True)

    class Meta:
        ordering = ("sort", "slug")

    def __str__(self) -> str:
        return f"{self.verb} — {self.name}"

    def get_absolute_url(self) -> str:
        return reverse(f"{self.slug}:index")

    @property
    def accent_token(self) -> str:
        return {"create": "--glow", "build": "--steel", "train": "--gold"}[self.slug]


class Milestone(TimeStamped, Published):
    """
    The honor line. `confirmed` is the guardrail — unconfirmed items stay in
    admin and never render on the site.
    """

    year = models.CharField(max_length=16, blank=True)
    title = models.CharField(max_length=140)
    detail = models.CharField(max_length=200, blank=True)
    confirmed = models.BooleanField(
        default=False,
        help_text="Only confirmed milestones are printed on the site.",
    )

    class Meta:
        ordering = ("sort", "-year")

    def __str__(self) -> str:
        return f"{self.year} {self.title}".strip()


class Inquiry(TimeStamped):
    """Anything that comes in from a contact form, tagged with the room it came from."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        READ = "read", "Read"
        REPLIED = "replied", "Replied"
        CLOSED = "closed", "Closed"

    world = models.ForeignKey(
        World, on_delete=models.SET_NULL, null=True, blank=True, related_name="inquiries"
    )
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    subject = models.CharField(max_length=160, blank=True)
    message = models.TextField()
    budget = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)],
        help_text="Optional, in whole dollars.",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NEW)
    source_path = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name_plural = "inquiries"

    def __str__(self) -> str:
        room = self.world.verb if self.world else "House"
        return f"{room} · {self.name} · {self.created_at:%Y-%m-%d}"
