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

    class Category(models.TextChoices):
        """The market a piece belongs to — how the portfolio is navigated."""

        WEDDING = "wedding", "Weddings"
        EVENT = "event", "Events"
        SCHOOL = "school", "Schools & Sports"
        LISTING = "listing", "Real estate & drone"
        BRAND = "brand", "Brand & business"
        STILLS = "stills", "Stills"

    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=140, unique=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.FILM)
    category = models.CharField(
        max_length=10,
        choices=Category.choices,
        default=Category.WEDDING,
        db_index=True,
        help_text="The market this piece belongs to. Drives the portfolio filter.",
    )
    year = models.CharField(max_length=8, blank=True)
    client = models.CharField(max_length=120, blank=True)
    location = models.CharField(
        max_length=120, blank=True, default="",
        help_text="Venue or town, e.g. Walker's Overlook · Walkersville, MD",
    )
    blurb = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    poster = models.ImageField(upload_to="create/posters/", blank=True)
    video_url = models.URLField(blank=True, help_text="Vimeo / YouTube embed or file URL.")
    instagram_url = models.URLField(
        blank=True,
        help_text="Public Instagram post or reel URL. Embedded on the work page.",
    )
    video_file = models.FileField(
        upload_to="create/reel/",
        blank=True,
        help_text="Web-ready derivative made by `manage.py ingest_reel`.",
    )
    duration_seconds = models.FloatField(null=True, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    source_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Where the master came from, so a re-ingest knows what it already has.",
    )
    aspect = models.CharField(
        max_length=8,
        choices=[("wide", "2.39:1"), ("video", "16:9"), ("tall", "4:5"), ("square", "1:1")],
        default="wide",
    )
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

    @property
    def playable(self) -> str:
        """The source the console should play, if there is one."""
        if self.video_file:
            return self.video_file.url
        return ""

    @property
    def runtime_label(self) -> str:
        if self.runtime:
            return self.runtime
        if not self.duration_seconds:
            return ""
        total = int(round(self.duration_seconds))
        return f"{total // 60}:{total % 60:02d}"

    @property
    def instagram_embed(self) -> str:
        """Instagram's own embed endpoint. Empty when no post is attached."""
        if not self.instagram_url:
            return ""
        return self.instagram_url.split("?")[0].rstrip("/") + "/embed"


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


class Method(TimeStamped, Published):
    """
    How the work gets made. The Create room is a shop window for content
    production, so the methods are the offer as much as the reel is.
    """

    name = models.CharField(max_length=80)
    kicker = models.CharField(max_length=40, blank=True, help_text="e.g. 01 / Pre")
    blurb = models.CharField(max_length=220)
    detail = models.TextField(blank=True)
    gear = models.CharField(
        max_length=160, blank=True, help_text="Comma separated. What it is shot on."
    )

    class Meta:
        ordering = ("sort", "name")

    def __str__(self) -> str:
        return self.name

    @property
    def gear_items(self) -> list[str]:
        return [item.strip() for item in self.gear.split(",") if item.strip()]


class Commission(TimeStamped):
    """
    A service request from the Oasis Media Visions site. Purpose-built for how
    film work actually gets booked: a service, a date, a place, and the story.

    Separate from the house Inquiry on purpose — this one carries the fields a
    videographer needs to quote, and it is what Oasis reads as an OMV enquiry.
    """

    class Service(models.TextChoices):
        WEDDING = "wedding", "Wedding film"
        EVENT = "event", "Event film"
        SCHOOL = "school", "School / sports film"
        LISTING = "listing", "Listing film & drone"
        BRAND = "brand", "Brand / business film"
        OTHER = "other", "Something else"

    class Status(models.TextChoices):
        NEW = "new", "New"
        READ = "read", "Read"
        QUOTED = "quoted", "Quoted"
        BOOKED = "booked", "Booked"
        CLOSED = "closed", "Closed"

    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    service = models.CharField(
        max_length=10, choices=Service.choices, default=Service.WEDDING, db_index=True
    )
    package = models.ForeignKey(
        "create.Package",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commissions",
        help_text="If they started from a package, it is recorded here.",
    )
    event_date = models.DateField(null=True, blank=True, help_text="If they have one.")
    location = models.CharField(
        max_length=160, blank=True, help_text="Venue or town the shoot is in."
    )
    details = models.TextField(help_text="What they are trying to make.")
    budget = models.PositiveIntegerField(
        null=True, blank=True, help_text="Optional, in whole dollars."
    )
    how_heard = models.CharField(max_length=120, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.NEW, db_index=True
    )
    source_path = models.CharField(max_length=200, blank=True)
    notified_oasis = models.BooleanField(
        default=False,
        help_text="Set once Oasis has picked this up as an enquiry, so it is not re-counted.",
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "commission request"
        verbose_name_plural = "commission requests"

    def __str__(self) -> str:
        return f"{self.get_service_display()} · {self.name} · {self.created_at:%Y-%m-%d}"

    @property
    def is_open(self) -> bool:
        return self.status in {self.Status.NEW, self.Status.READ, self.Status.QUOTED}
