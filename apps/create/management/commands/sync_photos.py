"""
Sync the Photography gallery from the committed manifest.

`static/omv/gallery_manifest.json` is the record of every still that ships with
the site (filename, style, sort, dimensions, featured flag). This command reads
it and upserts one Photo row per entry, so adding a photo is: drop the optimized
JPEG into static/omv/gallery/, add a manifest line, run this.

Idempotent and non-destructive: it matches rows by `image`, so re-running only
updates in place and never duplicates. It leaves `title`/`caption` alone (those
are curated in the admin, not in the manifest) and never deletes rows — pull a
photo by removing its manifest line and its Photo row by hand.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Upsert Photo rows from static/omv/gallery_manifest.json."

    def handle(self, *args, **opts):
        from apps.create.models import Photo

        manifest = Path(settings.BASE_DIR) / "static" / "omv" / "gallery_manifest.json"
        gallery = Path(settings.BASE_DIR) / "static" / "omv" / "gallery"
        if not manifest.exists():
            raise CommandError(f"No manifest at {manifest}")

        entries = json.loads(manifest.read_text())
        made = updated = missing = 0
        counts: dict[str, int] = {}
        for e in entries:
            image = e.get("image")
            if not image:
                continue
            if not (gallery / image).exists():
                self.stderr.write(f"skip (file missing): {image}")
                missing += 1
                continue
            _, created = Photo.objects.update_or_create(
                image=image,
                defaults={
                    "style": e.get("style", "wedding"),
                    "sort": e.get("sort", 100),
                    "width": e.get("width"),
                    "height": e.get("height"),
                    "is_featured": bool(e.get("is_featured")),
                    "is_live": True,
                },
            )
            made += created
            updated += (not created)
            counts[e.get("style", "?")] = counts.get(e.get("style", "?"), 0) + 1

        self.stdout.write(self.style.SUCCESS(
            f"Synced {made + updated} photos ({made} new, {updated} updated"
            + (f", {missing} missing" if missing else "") + ") → "
            + ", ".join(f"{k}:{v}" for k, v in sorted(counts.items()))
        ))
