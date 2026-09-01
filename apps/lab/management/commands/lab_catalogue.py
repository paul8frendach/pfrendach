"""Compare what the website offers with what the coach's LAB account holds.

    manage.py lab_catalogue                       # report
    manage.py lab_catalogue --brief               # + Manage Services instructions
    manage.py lab_catalogue --payload             # + the JSON a write endpoint would take
    manage.py lab_catalogue --file catalogue/other-coach.json

WHY A COMMAND AND NOT A SCREEN
    The audience is two developers wiring coaches up, not the coaches
    themselves. A command leaves its output in a terminal they can paste into an
    email to the coach, which is exactly the "go back and ask" step this is for.

WHAT IT WILL NOT DO
    It does not write to The LAB. There is no endpoint that writes coach
    configuration - see apps/lab/catalogue.py for why, and for what would have
    to change.
"""
from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.lab import store
from apps.lab.catalogue import (BLOCKS, DEGRADES, POLISH, BlockSpec,
                                ServiceSpec, block_manual_brief,
                                block_payload, block_questions, lab_payload,
                                manual_brief, questions, reconcile,
                                reconcile_blocks)
from apps.lab.client import client
from apps.lab.errors import LabError, LabRejected

DEFAULT_FILE = "catalogue/frendach.json"

_MARK = {BLOCKS: "BLOCKS  ", DEGRADES: "DEGRADES", POLISH: "POLISH  "}


class Command(BaseCommand):
    help = "Reconcile the site's service catalogue against the coach's LAB account."

    def add_arguments(self, parser):
        parser.add_argument("--file", default=DEFAULT_FILE)
        parser.add_argument("--brief", action="store_true",
                            help="Print Manage Services instructions for anything missing.")
        parser.add_argument("--payload", action="store_true",
                            help="Print the JSON the write endpoint takes.")
        parser.add_argument("--push", action="store_true",
                            help="Create or update the missing and drifted "
                                 "services in the coach's account.")
        parser.add_argument("--force", action="store_true",
                            help="With --push: overwrite services the coach has "
                                 "edited themselves since the last sync. Read "
                                 "what they changed first.")

    def handle(self, *args, **opts):
        path = Path(opts["file"])
        if not path.exists():
            raise CommandError(f"No catalogue at {path}.")
        data = json.loads(path.read_text())
        specs = [ServiceSpec.from_dict(row) for row in data.get("services", [])]
        if not specs:
            raise CommandError(f"{path} declares no services.")

        blocks = [BlockSpec.from_dict(row) for row in data.get("blocks", [])]

        live, notice = store.storefront()
        if notice:
            self.stdout.write(self.style.WARNING(f"Could not read The LAB: {notice}"))
            self.stdout.write("Reporting what the site declares only.\n")
        live_raw = [card.raw for card in live]

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n{path}  —  {len(specs)} declared, {len(live_raw)} live in The LAB\n"))

        result = reconcile(specs, live_raw)

        for spec, _found in result.matched:
            self.stdout.write(self.style.SUCCESS(f"  match    {spec.title}"))

        for spec, _found, differences in result.drifted:
            self.stdout.write(self.style.WARNING(f"  drift    {spec.title}"))
            for line in differences:
                self.stdout.write(f"             {line}")

        for spec in result.missing:
            self.stdout.write(self.style.ERROR(f"  missing  {spec.title}"))
            self.stdout.write("             not in the coach's account; the site "
                              "cannot sell it until it is")

        for found in result.unexpected:
            self.stdout.write(self.style.WARNING(
                f"  extra    {found.get('title')}"))
            self.stdout.write("             live in The LAB but not offered on the site")

        # ---- prepaid blocks --------------------------------------------
        if blocks:
            live_blocks, block_notice = store.prepaid_blocks()
            if block_notice:
                self.stdout.write(self.style.WARNING(
                    f"  Could not read blocks: {block_notice}"))
            block_result = reconcile_blocks(blocks, [c.raw for c in live_blocks])
            self.stdout.write("")
            for spec, _found in block_result.matched:
                self.stdout.write(self.style.SUCCESS(f"  match    {spec.title} (block)"))
            for spec, _found, differences in block_result.drifted:
                self.stdout.write(self.style.WARNING(f"  drift    {spec.title} (block)"))
                for line in differences:
                    self.stdout.write(f"             {line}")
            for spec in block_result.missing:
                self.stdout.write(self.style.ERROR(f"  missing  {spec.title} (block)"))
            for found in block_result.unexpected:
                self.stdout.write(self.style.WARNING(
                    f"  extra    {found.get('title')} (block)"))

        # ---- what to go back and ask -----------------------------------
        asked = False
        for spec in specs:
            gaps = questions(spec)
            if not gaps:
                continue
            if not asked:
                self.stdout.write(self.style.MIGRATE_HEADING(
                    "\nQuestions for the coach\n"))
                asked = True
            self.stdout.write(f"  {spec.title or spec.key}")
            for gap in gaps:
                self.stdout.write(f"    [{_MARK[gap.severity]}] {gap.what}")
                self.stdout.write(f"               ask: {gap.question}")
        service_keys = [s.key for s in specs]
        for spec in blocks:
            gaps = block_questions(spec, service_keys)
            if not gaps:
                continue
            if not asked:
                self.stdout.write(self.style.MIGRATE_HEADING(
                    "\nQuestions for the coach\n"))
                asked = True
            self.stdout.write(f"  {spec.title or spec.key} (block)")
            for gap in gaps:
                self.stdout.write(f"    [{_MARK[gap.severity]}] {gap.what}")
                self.stdout.write(f"               ask: {gap.question}")

        if not asked:
            self.stdout.write(self.style.SUCCESS(
                "\nEvery declared service is described completely.\n"))

        # ---- how to enter them -----------------------------------------
        if opts["brief"] and (result.missing or result.drifted):
            self.stdout.write(self.style.MIGRATE_HEADING(
                "\nEnter these in The LAB\n"))
            for spec in result.missing + [s for s, _, _ in result.drifted]:
                for line in manual_brief(spec):
                    self.stdout.write(f"  {line}")
                self.stdout.write("")
            for spec in blocks:
                for line in block_manual_brief(spec):
                    self.stdout.write(f"  {line}")
                self.stdout.write("")

        if opts["payload"]:
            self.stdout.write(self.style.MIGRATE_HEADING(
                "\nPayload for a write endpoint that does not exist yet\n"))
            self.stdout.write(json.dumps(
                [lab_payload(s) for s in specs if not questions(s)
                 or not any(g.is_blocking for g in questions(s))], indent=2))

        if opts["push"]:
            # Order matters: services first, because a block names the service
            # it buys sessions of and The LAB refuses one whose service is not
            # there yet.
            self._push(specs, result, force=opts["force"])
            self._push_blocks(blocks, force=opts["force"])
            self._verify(specs, blocks)

        blocking = sum(1 for s in specs for g in questions(s) if g.is_blocking)
        self.stdout.write("")
        self.stdout.write(
            f"{len(result.matched)} match, {len(result.drifted)} drifted, "
            f"{len(result.missing)} missing, {len(result.unexpected)} extra, "
            f"{blocking} blocking question(s).")

    def _push(self, specs, result, *, force: bool):
        """Write the missing and drifted services into the coach's account.

        Only those two: a service that already matches needs no write, and
        writing it anyway would move `api_synced_at` for no reason and make the
        next genuine coach edit harder to see.
        """
        wanted = list(result.missing) + [spec for spec, _, _ in result.drifted]
        if not wanted:
            self.stdout.write(self.style.SUCCESS(
                "\nNothing to push - the account already matches.\n"))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("\nPushing to The LAB\n"))
        api = client()
        for spec in wanted:
            blocking = [g for g in questions(spec) if g.is_blocking]
            if blocking:
                # Refusing here rather than letting The LAB refuse means the
                # message names the question to ask the coach, not the field.
                self.stdout.write(self.style.ERROR(f"  skipped  {spec.title or spec.key}"))
                for gap in blocking:
                    self.stdout.write(f"             ask: {gap.question}")
                continue

            payload = lab_payload(spec)
            payload["external_ref"] = spec.key
            if force:
                payload["force"] = True
            try:
                answer = api.write_service(payload)
            except LabRejected as exc:
                if exc.code == "coach_edited":
                    self.stdout.write(self.style.WARNING(
                        f"  refused  {spec.title} - the coach edited this in The LAB"))
                    self.stdout.write(f"             {exc.public_message}")
                else:
                    self.stdout.write(self.style.ERROR(f"  failed   {spec.title}"))
                    self.stdout.write(f"             {exc}")
                continue
            except LabError as exc:
                self.stdout.write(self.style.ERROR(f"  failed   {spec.title}"))
                self.stdout.write(f"             {exc}")
                continue

            verb = "created" if answer.get("created") else "updated"
            self.stdout.write(self.style.SUCCESS(
                f"  {verb:<8} {answer.get('title')}  (id {answer.get('id')})"))
            for name in answer.get("unmatched_locations") or []:
                self.stdout.write(self.style.WARNING(
                    f"             location not found in the coach's account: {name}"))
                self.stdout.write(
                    "             ask them to add it in The LAB; until then this "
                    "service is enquiry-only")

    def _push_blocks(self, blocks, *, force: bool):
        if not blocks:
            return
        api = client()
        for spec in blocks:
            blocking = [g for g in block_questions(spec, [spec.service_key])
                        if g.is_blocking and g.field != "service_key"]
            if blocking:
                self.stdout.write(self.style.ERROR(f"  skipped  {spec.title} (block)"))
                for gap in blocking:
                    self.stdout.write(f"             ask: {gap.question}")
                continue
            payload = block_payload(spec)
            if force:
                payload["force"] = True
            try:
                answer = api.write_block(payload)
            except LabRejected as exc:
                label = ("the coach edited this in The LAB"
                         if exc.code == "coach_edited" else exc.public_message)
                self.stdout.write(self.style.WARNING(
                    f"  refused  {spec.title} (block) — {label}"))
                continue
            except LabError as exc:
                self.stdout.write(self.style.ERROR(
                    f"  failed   {spec.title} (block)"))
                self.stdout.write(f"             {exc}")
                continue
            verb = "created" if answer.get("created") else "updated"
            self.stdout.write(self.style.SUCCESS(
                f"  {verb:<8} {answer.get('title')} (block, id {answer.get('id')})"))

    def _verify(self, specs, blocks):
        """Read the account back and prove it says what the site will render.

        This is the half that makes provisioning trustworthy. Writing returns
        The LAB's word for what it did; verifying asks the account itself,
        with the cache bypassed, and compares it to what this site is about to
        put in front of a parent. A push that reported success and left a price
        disagreeing is exactly the failure the whole exercise is meant to end.
        """
        self.stdout.write(self.style.MIGRATE_HEADING("\nVerifying the account\n"))

        live, notice = store.storefront(fresh=True)
        if notice:
            self.stdout.write(self.style.ERROR(
                f"  could not read the account back: {notice}"))
            return
        result = reconcile(specs, [card.raw for card in live])

        live_blocks, block_notice = store.prepaid_blocks(fresh=True)
        block_result = reconcile_blocks(
            blocks, [] if block_notice else [c.raw for c in live_blocks])

        clean = True
        for spec, _found, differences in result.drifted + [
                (s, f, d) for s, f, d in block_result.drifted]:
            clean = False
            self.stdout.write(self.style.WARNING(f"  still differs  {spec.title}"))
            for line in differences:
                self.stdout.write(f"                 {line}")
        for spec in result.missing + block_result.missing:
            clean = False
            self.stdout.write(self.style.ERROR(
                f"  still missing  {spec.title} — the write did not land"))

        if clean:
            self.stdout.write(self.style.SUCCESS(
                f"  {len(result.matched)} service(s) and "
                f"{len(block_result.matched)} block(s) confirmed in the account, "
                "matching what this site renders."))
