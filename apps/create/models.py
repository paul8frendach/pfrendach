"""
Vision Oasis — the Create world.

Work is the portfolio. Packages are the storefront. Vision Oasis is credited on
the work; it never sits on the house mark.
"""

from django.db import models
from django.urls import reverse

from apps.house.models import Published, TimeStamped


class Work(TimeStamped, Published):
    """A film, a reel, or a set of stills."""

    class Kind(models.TextChoices):
        FILM = "film", "Film"
        REEL = "reel", "Reel"
        STILLS = "stills", "Stills"
        SESSION = "session", "Session film"

    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=140, unique=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.FILM)
    year = models.CharField(max_length=8, blank=True)
    client = models.CharField(max_length=120, blank=True)
    blurb = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    poster = models.ImageField(upload_to="create/posters/", blank=True)
    video_url = models.URLField(blank=True, help_text="Vimeo / YouTube embed or file URL.")
    runtime = models.CharField(max_length=20, blank=True, help_text="e.g. 1:42")
    credit = models.CharField(max_length=120, default="Vision Oasis")
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ("sort", "-year", "title")
        verbose_name_plural = "work"

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("create:work_detail", args=[self.slug])


class Package(TimeStamped, Published):
    """A content service someone can actually buy."""

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)
    summary = models.CharField(max_length=200)
    deliverables = models.TextField(help_text="One deliverable per line.")
    turnaround = models.CharField(max_length=60, blank=True, default="2 weeks")
    price_from = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    price_note = models.CharField(max_length=80, blank=True, default="On request")
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ("sort", "name")

    def __str__(self) -> str:
        return self.name

    @property
    def deliverable_lines(self) -> list[str]:
        return [line.strip() for line in self.deliverables.splitlines() if line.strip()]

    @property
    def price_label(self) -> str:
        if self.price_from is None:
            return self.price_note or "On request"
        return f"From ${int(self.price_from)}"
