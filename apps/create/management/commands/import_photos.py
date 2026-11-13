"""
Import a curated set of OMV stills into the Photography sub-world.

Reads the finished JPEGs off the drive, writes web-optimized copies into
static/omv/gallery/ (committed, so they ship with the site and need no media
server), and (re)builds the Photo rows grouped by style. Idempotent: it clears
the gallery rows and regenerates, so re-running is safe.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image, ImageOps

# (style, drive filename). Order within a style is display order.
CURATED = [
    ("wedding", "IMG_2900.jpg"),
    ("wedding", "IMG_2901.jpg"),
    ("wedding", "IMG_2907.jpg"),
    ("wedding", "IMG_7649.jpg"),
    ("wedding", "IMG_8698.jpg"),
    ("wedding", "IMG_8703.jpg"),
    ("portrait", "IMG_1066.JPG"),
    ("portrait", "36C8CF8E-93AA-4C39-9D5C-C57794B9B093.JPG"),
    ("portrait", "IMG_1882.jpg"),
    ("portrait", "IMG_2161.jpg"),
    ("portrait", "IMG_2453.jpg"),
    ("portrait", "IMG_2742.jpg"),
    ("sports", "IMG_6271.jpg"),
    ("sports", "20231124-IMG_9161.jpg"),
    ("sports", "20231124-IMG_9231.jpg"),
    ("sports", "IMG_5463.jpg"),
    ("sports", "IMG_6093.jpg"),
    ("sports", "IMG_6485 2.jpg"),
    ("aerial", "DJI_0016.jpg"),
    ("aerial", "Temple Football 6 bit.jpg"),
]
FEATURED = {"wedding-1.jpg", "portrait-1.jpg", "sports-1.jpg", "aerial-1.jpg"}
MAX_EDGE = 2200
QUALITY = 86


class Command(BaseCommand):
    help = "Import curated OMV stills into the Photography sub-world."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            default="/Volumes/OMV JAN 2024/OASIS PHOTOS",
            help="Source folder holding the finished JPEGs.",
        )

    def handle(self, *args, **opts):
        from apps.create.models import Photo

        src_dir = Path(opts["dir"])
        out_dir = Path(settings.BASE_DIR) / "static" / "omv" / "gallery"
        out_dir.mkdir(parents=True, exist_ok=True)

        Photo.objects.all().delete()

        counts: dict[str, int] = {}
        made = 0
        for style, fname in CURATED:
            src = src_dir / fname
            if not src.exists():
                self.stderr.write(f"skip (missing): {fname}")
                continue
            counts[style] = counts.get(style, 0) + 1
            out_name = f"{style}-{counts[style]}.jpg"
            try:
                im = Image.open(src)
                im = ImageOps.exif_transpose(im).convert("RGB")
                im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
                im.save(out_dir / out_name, "JPEG", quality=QUALITY, optimize=True, progressive=True)
                w, h = im.size
            except Exception as exc:  # noqa: BLE001
                self.stderr.write(f"FAILED {fname}: {exc}")
                continue
            Photo.objects.create(
                image=out_name,
                style=style,
                width=w,
                height=h,
                is_featured=out_name in FEATURED,
                sort=counts[style] * 10,
                is_live=True,
            )
            made += 1

        self.stdout.write(self.style.SUCCESS(
            f"Imported {made} photos into static/omv/gallery/ → "
            + ", ".join(f"{k}:{v}" for k, v in counts.items())
        ))
