"""
Ingest a folder of footage into the Create room's portfolio console.

Same shape as the workers in Debrief and Core: probe with ffprobe, derive with
ffmpeg, record in the database, and be safe to run again. Masters are never
touched or moved — only read.

    python manage.py ingest_reel "~/Desktop/SIMMONS PORTFOLIO"
    python manage.py ingest_reel ~/Downloads/instagram-export --kind reel
    python manage.py ingest_reel <folder> --force        # rebuild derivatives

Instagram: use Instagram's own export (Settings -> Accounts Centre -> Your
information and permissions -> Download your information). It hands you your
videos at full quality in a folder, which this command reads like any other.
Scraping the site is neither necessary nor allowed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.create.models import Work

VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}

# Anything wider than this is downscaled for the web. The masters stay where
# they are; this only decides what a browser has to download.
MAX_WIDTH = 1280
POSTER_WIDTH = 960


class Command(BaseCommand):
    help = "Ingest a folder of video into the Create portfolio console."

    def add_arguments(self, parser):
        parser.add_argument("folder", help="Folder of masters to read. Never modified.")
        parser.add_argument("--kind", default=Work.Kind.REEL,
                            choices=[c[0] for c in Work.Kind.choices])
        parser.add_argument("--limit", type=int, default=0, help="Stop after N files.")
        parser.add_argument("--max-seconds", type=float, default=30.0,
                            help="Cap the web derivative (0 = no cap). A console "
                                 "clip is a teaser; nobody downloads the whole film.")
        parser.add_argument("--start", type=float, default=0.0,
                            help="Seconds into the master to start the derivative.")
        parser.add_argument("--force", action="store_true",
                            help="Rebuild derivatives for files already ingested.")
        parser.add_argument("--live", action="store_true",
                            help="Publish immediately. Off by default so nothing "
                                 "appears on the site before he has looked at it.")

    def handle(self, *args, **options):
        for tool in ("ffprobe", "ffmpeg"):
            if shutil.which(tool) is None:
                raise CommandError(f"{tool} is not on PATH.")

        folder = Path(options["folder"]).expanduser()
        if not folder.is_dir():
            raise CommandError(f"Not a folder: {folder}")

        masters = sorted(
            p for p in folder.rglob("*")
            if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES and not p.name.startswith(".")
        )
        if options["limit"]:
            masters = masters[: options["limit"]]

        if not masters:
            self.stdout.write(self.style.WARNING(f"No video found under {folder}"))
            return

        made = skipped = failed = 0
        for master in masters:
            try:
                created = self._ingest(master, options)
            except Exception as exc:                      # noqa: BLE001 - report, continue
                failed += 1
                self.stdout.write(self.style.ERROR(f"  ✗ {master.name}: {exc}"))
                continue
            if created is None:
                skipped += 1
            else:
                made += 1

        self.stdout.write(self.style.SUCCESS(
            f"{made} ingested · {skipped} already present · {failed} failed"
        ))
        if made and not options["live"]:
            self.stdout.write(
                "Nothing is published yet — set them live in the admin, or re-run "
                "with --live."
            )

    # ------------------------------------------------------------------ steps

    def _probe(self, path: Path) -> dict:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", str(path)],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(out.stdout)
        video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
        if video is None:
            raise RuntimeError("no video stream")
        duration = float(data.get("format", {}).get("duration") or 0) or None
        return {
            "width": int(video.get("width") or 0) or None,
            "height": int(video.get("height") or 0) or None,
            "duration": duration,
        }

    def _aspect_for(self, width: int | None, height: int | None) -> str:
        if not width or not height:
            return "wide"
        ratio = width / height
        if ratio < 0.85:
            return "tall"
        if ratio < 1.15:
            return "square"
        if ratio > 2.1:
            return "wide"
        return "video"

    def _ingest(self, master: Path, options) -> Work | None:
        slug = slugify(master.stem)[:140] or slugify(master.parent.name)[:140]
        existing = Work.objects.filter(slug=slug).first()
        if existing and existing.video_file and not options["force"]:
            return None

        info = self._probe(master)
        work = existing or Work(slug=slug)
        work.title = work.title or master.stem.replace("_", " ").replace("-", " ").strip()
        work.kind = options["kind"]
        work.width = info["width"]
        work.height = info["height"]
        # The duration that matters to the page is the derivative's, not the
        # master's — the console shows what a visitor can actually watch.
        cap = float(options["max_seconds"])
        full = info["duration"]
        work.duration_seconds = min(full, cap) if (full and cap > 0) else full
        work.aspect = self._aspect_for(info["width"], info["height"])
        work.source_path = str(master)
        work.is_live = bool(options["live"])
        work.save()

        tmp = Path(subprocess.run(["mktemp", "-d"], capture_output=True, text=True,
                                  check=True).stdout.strip())
        try:
            derivative = tmp / f"{slug}.mp4"
            poster = tmp / f"{slug}.jpg"

            width = info["width"] or MAX_WIDTH
            scale = f"scale='min({MAX_WIDTH},iw)':-2" if width > MAX_WIDTH else "scale=trunc(iw/2)*2:trunc(ih/2)*2"

            start = float(options["start"])
            cap = float(options["max_seconds"])

            # -ss BEFORE -i seeks by keyframe without decoding what it skips.
            # On a 1.6 GB master that is the difference between seconds and
            # minutes, and this machine has 8 GB — a full-length transcode here
            # does not fail, it swaps and stops responding.
            cmd = ["ffmpeg", "-y", "-loglevel", "error"]
            if start > 0:
                cmd += ["-ss", str(start)]
            cmd += ["-i", str(master)]
            if cap > 0:
                cmd += ["-t", str(cap)]
            # faststart so the browser can begin playing before the whole file
            # has arrived — the console is judged on how fast the first frame lands.
            cmd += ["-vf", scale, "-c:v", "libx264", "-crf", "23", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    "-c:a", "aac", "-b:a", "128k", "-ac", "2", str(derivative)]
            subprocess.run(cmd, check=True, capture_output=True)

            # A little way in, so the poster is never a black first frame.
            seek = start + max(0.5, min(2.0, (info["duration"] or 5) * 0.1))
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(seek), "-i", str(master),
                 "-frames:v", "1", "-vf", f"scale='min({POSTER_WIDTH},iw)':-2",
                 "-q:v", "3", str(poster)],
                check=True, capture_output=True,
            )

            with derivative.open("rb") as fh:
                work.video_file.save(derivative.name, File(fh), save=False)
            with poster.open("rb") as fh:
                work.poster.save(poster.name, File(fh), save=False)
            work.save()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        self.stdout.write(
            f"  ✓ {work.title}  {work.width}x{work.height}  {work.runtime_label}"
        )
        return work
