"""
Build — the web world.

Projects are proof. Capabilities are the software and features he has already
built that a client could put to work.
"""

from django.db import models
from django.urls import reverse

from apps.house.models import Published, TimeStamped


class Project(TimeStamped, Published):
    """A site or product he shipped."""

    class Stage(models.TextChoices):
        LIVE = "live", "Live"
        BUILDING = "building", "In build"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    tagline = models.CharField(max_length=200)
    role = models.CharField(max_length=120, default="Design and build")
    year = models.CharField(max_length=8, blank=True)
    stage = models.CharField(max_length=10, choices=Stage.choices, default=Stage.LIVE)
    url = models.URLField(blank=True)
    stack = models.CharField(
        max_length=200, blank=True, help_text="Comma separated. Django, Postgres, ffmpeg…"
    )
    problem = models.TextField(blank=True)
    approach = models.TextField(blank=True)
    outcome = models.TextField(blank=True)
    shot = models.ImageField(upload_to="build/shots/", blank=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ("sort", "-year", "name")

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("build:project_detail", args=[self.slug])

    @property
    def stack_items(self) -> list[str]:
        return [item.strip() for item in self.stack.split(",") if item.strip()]


class Capability(TimeStamped, Published):
    """A feature already built and reusable — the part a client is buying time out of."""

    title = models.CharField(max_length=100)
    blurb = models.CharField(max_length=220)
    detail = models.TextField(blank=True)
    glyph = models.CharField(
        max_length=8, blank=True, help_text="One character or short symbol for the card."
    )
    proof_project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="capabilities"
    )

    class Meta:
        ordering = ("sort", "title")
        verbose_name_plural = "capabilities"

    def __str__(self) -> str:
        return self.title
