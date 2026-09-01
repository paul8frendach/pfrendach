"""Tests for the LAB wrapper.

These never touch the network. The client is exercised against a fake urlopen,
which is the point: the failure modes worth pinning down are the ones that only
happen when The LAB is unreachable, lapsed or angry, and none of those can be
produced on demand against a real server.

`tests_live.py` holds the handful that do want a real LAB.
"""
from __future__ import annotations

import io
import json
import urllib.error
from unittest import mock

from django.test import SimpleTestCase, TestCase, override_settings

from apps.lab import store
from apps.lab.client import LabClient
from apps.lab.errors import (LabAccountError, LabConfigError, LabRejected,
                             LabUnavailable)
from apps.lab.intake import build_form_class, payload_from
from apps.lab.presenters import service_card

SETTINGS = dict(LAB_API_BASE="http://lab.test", LAB_API_KEY="lab_test_abc123",
                LAB_CACHE_SECONDS=0)


def _response(body: dict, status: int = 200):
    raw = json.dumps(body).encode()
    fake = mock.MagicMock()
    fake.read.return_value = raw
    fake.status = status
    fake.__enter__.return_value = fake
    fake.__exit__.return_value = False
    return fake


def _http_error(status: int, code: str, message: str = "nope"):
    body = json.dumps({"error": {"code": code, "message": message}}).encode()
    return urllib.error.HTTPError("http://lab.test", status, message, {},
                                  io.BytesIO(body))


@override_settings(**SETTINGS)
class ClientTests(SimpleTestCase):

    def test_names_itself_and_sends_the_key(self):
        """Trap: a default library User-Agent gets Cloudflare's HTML 403."""
        with mock.patch("urllib.request.urlopen", return_value=_response({"ok": 1})) as opener:
            LabClient().get("me")
        request = opener.call_args[0][0]
        self.assertEqual(request.get_header("Authorization"), "Bearer lab_test_abc123")
        self.assertIn("paulfrendach", request.get_header("User-agent").lower())

    def test_post_always_carries_an_idempotency_key(self):
        with mock.patch("urllib.request.urlopen", return_value=_response({"lead_id": 1})) as opener:
            LabClient().create_lead({"payer": {"email": "a@b.c"}})
        self.assertTrue(opener.call_args[0][0].get_header("Idempotency-key"))

    def test_minted_idempotency_key_is_not_a_row_id(self):
        """Dev, staging and prod all start at pk 1, so `lead-1` collides."""
        seen = set()
        with mock.patch("urllib.request.urlopen", return_value=_response({"lead_id": 1})) as opener:
            for _ in range(3):
                LabClient().create_lead({"payer": {}})
                seen.add(opener.call_args[0][0].get_header("Idempotency-key"))
        self.assertEqual(len(seen), 3)
        self.assertTrue(all(len(k) >= 32 for k in seen))

    def test_lapsed_subscription_is_an_account_problem(self):
        with mock.patch("urllib.request.urlopen",
                        side_effect=_http_error(403, "subscription_required")):
            with self.assertRaises(LabAccountError):
                LabClient().services()

    def test_missing_scope_is_a_config_problem(self):
        with mock.patch("urllib.request.urlopen",
                        side_effect=_http_error(403, "missing_scope")):
            with self.assertRaises(LabConfigError):
                LabClient().services()

    def test_duplicate_email_is_rejected_not_broken(self):
        with mock.patch("urllib.request.urlopen",
                        side_effect=_http_error(409, "email_belongs_to_account",
                                                "Ask them to sign in instead.")):
            with self.assertRaises(LabRejected) as caught:
                LabClient().create_lead({"payer": {}})
        self.assertIn("sign in", caught.exception.public_message)

    def test_connection_refused_is_unavailable(self):
        with mock.patch("urllib.request.urlopen",
                        side_effect=urllib.error.URLError("refused")):
            with self.assertRaises(LabUnavailable):
                LabClient().services()

    def test_html_where_json_belongs_is_named(self):
        """Cloudflare's 403 is HTML. Reporting it as a parse error hides it."""
        fake = mock.MagicMock()
        fake.read.return_value = b"<html>403</html>"
        fake.status = 200
        fake.__enter__.return_value = fake
        fake.__exit__.return_value = False
        with mock.patch("urllib.request.urlopen", return_value=fake):
            with self.assertRaises(LabUnavailable) as caught:
                LabClient().services()
        self.assertIn("User-Agent", str(caught.exception))

    @override_settings(LAB_API_BASE="", LAB_API_KEY="")
    def test_unconfigured_is_its_own_error(self):
        with self.assertRaises(LabConfigError):
            LabClient().me()


@override_settings(**SETTINGS)
class StoreTests(TestCase):
    """The read layer never raises, and never invents a price."""

    def test_outage_yields_a_notice_and_no_cards(self):
        with mock.patch("urllib.request.urlopen",
                        side_effect=urllib.error.URLError("down")):
            cards, notice = store.storefront()
        self.assertEqual(cards, [])
        self.assertTrue(notice)
        self.assertNotIn("$", notice)

    def test_disabled_form_is_not_an_error(self):
        with mock.patch("urllib.request.urlopen",
                        return_value=_response({"is_enabled": False})):
            definition, notice = store.intake_definition()
        self.assertIsNone(definition)
        self.assertTrue(notice)


class PresenterTests(SimpleTestCase):

    def test_range_says_what_it_varies_with(self):
        card = service_card({
            "id": 2, "title": "Small Group", "type": "Training",
            "is_per_athlete": True, "duration_minutes": 75,
            "price": {"mode": "tiered", "from": "90.00", "to": "180.00"},
            "booking": {"mode": "enquiry", "reason": "no_location"},
        })
        self.assertEqual(card.price_label, "$90 – $180")
        self.assertIn("players", card.price_note)

    def test_no_price_reads_as_on_request(self):
        card = service_card({"id": 4, "title": "Block", "type": "Training",
                             "price": None, "booking": {"mode": "enquiry"}})
        self.assertEqual(card.price_label, "On request")
        self.assertTrue(card.is_enquiry)

    def test_whole_dollars_lose_the_decimals(self):
        card = service_card({"id": 1, "title": "1v1", "type": "Training",
                             "price": {"from": "85.00"}, "booking": {"mode": "calendar"}})
        self.assertEqual(card.price_label, "$85")
        self.assertFalse(card.is_enquiry)


DEFINITION = {
    "is_enabled": True,
    "collect": {"athlete_name": True, "parent_name": True, "email": True,
                "phone": True, "age": True, "experience": True, "notes": True},
    "fields": [
        {"id": 1, "label": "Position", "type": "dropdown", "required": True,
         "per_athlete": True, "options": ["Winger", "Keeper"]},
        {"id": 4, "label": "How did you hear?", "type": "checkboxes",
         "required": False, "per_athlete": False, "options": ["Word", "Instagram"]},
    ],
}


class IntakeTests(SimpleTestCase):

    def test_the_coach_decides_the_questions(self):
        form = build_form_class(DEFINITION)()
        self.assertIn("athlete_0_custom_1", form.fields)
        self.assertIn("custom_4", form.fields)
        self.assertEqual(form.fields["athlete_0_custom_1"].label, "Position")

    def test_a_question_removed_in_the_lab_disappears_here(self):
        trimmed = {**DEFINITION, "fields": []}
        form = build_form_class(trimmed)()
        self.assertNotIn("athlete_0_custom_1", form.fields)

    def test_only_the_first_player_inherits_required(self):
        form = build_form_class(DEFINITION, athletes=2)()
        self.assertTrue(form.fields["athlete_0_custom_1"].required)
        self.assertFalse(form.fields["athlete_1_custom_1"].required)

    def test_exactly_one_age_representation_is_sent(self):
        cleaned = {
            "payer_email": "a@b.c",
            "athlete_0_first_name": "Mia", "athlete_0_last_name": "Ruiz",
            "athlete_0_age_type": "year", "athlete_0_birth_year": 2010,
            "athlete_0_age_range": "11-14",   # also filled in; must be ignored
        }
        row = payload_from(cleaned, DEFINITION)["athletes"][0]
        self.assertEqual(row["birth_year"], "2010")
        self.assertNotIn("age_range", row)
        self.assertNotIn("birthday", row)

    def test_empty_extra_blocks_are_dropped(self):
        cleaned = {"payer_email": "a@b.c",
                   "athlete_0_first_name": "Mia",
                   "athlete_1_first_name": "", "athlete_1_last_name": ""}
        payload = payload_from(cleaned, DEFINITION, athletes=2)
        self.assertEqual(len(payload["athletes"]), 1)

    def test_checkbox_answers_read_as_a_sentence(self):
        cleaned = {"payer_email": "a@b.c", "athlete_0_first_name": "Mia",
                   "custom_4": ["Word", "Instagram"]}
        payload = payload_from(cleaned, DEFINITION)
        self.assertEqual(payload["answers"]["How did you hear?"], "Word, Instagram")

    def test_experience_is_mirrored_into_answers(self):
        """The LAB accepts `experience` and stores it nowhere. Until that
        changes, the answers blob is what actually reaches the coach."""
        cleaned = {"payer_email": "a@b.c", "athlete_0_first_name": "Mia",
                   "athlete_0_experience": "Travel club, 4 years"}
        row = payload_from(cleaned, DEFINITION)["athletes"][0]
        self.assertEqual(row["experience"], "Travel club, 4 years")
        self.assertEqual(row["answers"]["Experience so far"], "Travel club, 4 years")

    def test_answers_are_keyed_by_label_not_id(self):
        """The coach reads these in a chat thread. '3: Midfield' is not legible."""
        cleaned = {"payer_email": "a@b.c", "athlete_0_first_name": "Mia",
                   "athlete_0_custom_1": "Winger"}
        row = payload_from(cleaned, DEFINITION)["athletes"][0]
        self.assertIn("Position", row["answers"])

    def test_athlete_cap_matches_the_api(self):
        form = build_form_class(DEFINITION, athletes=99)()
        self.assertIn("athlete_11_first_name", form.fields)
        self.assertNotIn("athlete_12_first_name", form.fields)


@override_settings(LAB_API_BASE="http://lab.test", LAB_API_KEY="lab_live_real",
                   LAB_CACHE_SECONDS=0, LAB_ALLOW_LIVE_WRITES=False)
class LiveKeyGuardTests(SimpleTestCase):
    """A live key on a dev box reads freely and writes only when armed."""

    def test_reads_are_never_blocked(self):
        with mock.patch("urllib.request.urlopen", return_value=_response({"services": []})):
            self.assertEqual(LabClient().services(), [])

    def test_unarmed_live_write_never_reaches_the_network(self):
        with mock.patch("urllib.request.urlopen") as opener:
            with self.assertRaises(LabConfigError) as caught:
                LabClient().create_lead({"payer": {"email": "a@b.c"}})
        opener.assert_not_called()
        self.assertIn("LAB_ALLOW_LIVE_WRITES", str(caught.exception))

    @override_settings(LAB_ALLOW_LIVE_WRITES=True)
    def test_armed_live_write_goes_through(self):
        with mock.patch("urllib.request.urlopen",
                        return_value=_response({"lead_id": 9})) as opener:
            result = LabClient().create_lead({"payer": {"email": "a@b.c"}})
        opener.assert_called_once()
        self.assertEqual(result["lead_id"], 9)

    @override_settings(LAB_API_KEY="lab_test_sandbox")
    def test_test_keys_are_unaffected(self):
        with mock.patch("urllib.request.urlopen",
                        return_value=_response({"lead_id": 1})) as opener:
            LabClient().create_lead({"payer": {}})
        opener.assert_called_once()


class RatePriceNoteTests(SimpleTestCase):
    """An hourly rate must not print the same figure twice."""

    def test_one_hour_at_an_hourly_rate_says_per_hour(self):
        card = service_card({
            "id": 5, "title": "Soccer Training", "type": "Training",
            "duration_minutes": 60, "is_per_athlete": True,
            "price": {"mode": "rate", "from": "70.00", "to": None,
                      "from_hourly": "70.00"},
            "booking": {"mode": "calendar"},
        })
        self.assertEqual(card.price_label, "$70")
        self.assertEqual(card.price_note, "per hour")

    def test_a_longer_session_still_names_the_rate(self):
        card = service_card({
            "id": 6, "title": "Long", "type": "Training",
            "duration_minutes": 90, "is_per_athlete": True,
            "price": {"mode": "rate", "from": "105.00", "to": None,
                      "from_hourly": "70.00"},
            "booking": {"mode": "calendar"},
        })
        self.assertEqual(card.price_label, "$105")
        self.assertEqual(card.price_note, "$70 per hour")


class SlotTests(SimpleTestCase):
    """Times are printed as The LAB sent them, in the coach's own zone."""

    AVAILABILITY = {
        "next": "choose_slot",
        "service": {"id": 5, "title": "Soccer Training"},
        "location": {"id": 45, "name": "Don Henderson Field (Swarthmore)"},
        "timezone": "America/New_York",
        "days": [
            {"date": "2026-09-03", "slots": [
                {"start": "2026-09-03T18:00:00-04:00", "display_time": "6:00 PM"}]},
            {"date": "2026-09-10", "slots": [
                {"start": "2026-09-10T18:00:00-04:00", "display_time": "6:00 PM"}]},
        ],
    }

    def _card(self):
        return service_card({"id": 5, "title": "Soccer Training", "type": "Training",
                             "price": {"from": "70.00"},
                             "booking": {"mode": "calendar"}})

    def test_the_coachs_wall_clock_time_survives(self):
        """A 6pm session in Swarthmore must not become 10pm on the website."""
        from apps.lab.presenters import slot_cards
        slots = slot_cards(self.AVAILABILITY, self._card())
        self.assertEqual(slots[0].time_label, "6:00 PM")
        self.assertEqual(slots[0].timezone, "America/New_York")
        self.assertIn("-04:00", slots[0].starts_at)

    def test_the_day_reads_as_a_date_not_a_number(self):
        from apps.lab.presenters import slot_cards
        slots = slot_cards(self.AVAILABILITY, self._card())
        self.assertEqual(slots[0].day_label, "Thursday 3 September")

    def test_limit_is_respected_across_days(self):
        from apps.lab.presenters import slot_cards
        self.assertEqual(len(slot_cards(self.AVAILABILITY, self._card(), limit=1)), 1)

    def test_the_slot_carries_the_time_into_the_enquiry(self):
        from apps.lab.presenters import slot_cards
        url = slot_cards(self.AVAILABILITY, self._card())[0].url
        self.assertIn("service=5", url)
        self.assertIn("when=", url)


@override_settings(**SETTINGS)
class NextOpenTests(TestCase):
    """Enquiry-only services are never asked for availability."""

    def test_enquiry_only_services_are_skipped(self):
        asked = []
        def spy(request, timeout=None, **kw):
            url = request.get_full_url()
            asked.append(url)
            if "/services" in url:
                return _response({"services": [
                    {"id": 4, "title": "Block", "type": "Training", "price": None,
                     "booking": {"mode": "enquiry", "reason": "no_packages"}},
                ]})
            return _response({})
        with mock.patch("urllib.request.urlopen", side_effect=spy):
            slots, _ = store.next_open()
        self.assertEqual(slots, [])
        self.assertFalse([u for u in asked if "availability" in u])

    def test_an_availability_failure_does_not_break_the_page(self):
        def flaky(request, timeout=None, **kw):
            url = request.get_full_url()
            if "/services" in url:
                return _response({"services": [
                    {"id": 5, "title": "Soccer Training", "type": "Training",
                     "price": {"from": "70.00"}, "booking": {"mode": "calendar"}},
                ]})
            raise urllib.error.URLError("availability down")
        with mock.patch("urllib.request.urlopen", side_effect=flaky):
            slots, notice = store.next_open()
        self.assertEqual(slots, [])


class TestIsolationTests(SimpleTestCase):
    """The suite must never be able to reach a real coach's account."""

    def test_lab_is_unconfigured_under_the_test_runner(self):
        from django.conf import settings
        self.assertEqual(settings.LAB_API_BASE, "")
        self.assertEqual(settings.LAB_API_KEY, "")
        self.assertFalse(settings.LAB_ALLOW_LIVE_WRITES)

    def test_an_unmocked_call_fails_locally_rather_than_dialling_out(self):
        with mock.patch("urllib.request.urlopen") as opener:
            with self.assertRaises(LabConfigError):
                LabClient().services()
        opener.assert_not_called()


# --------------------------------------------------------------- catalogue

from apps.lab.catalogue import (BLOCKS, DEGRADES, ServiceSpec, lab_payload,
                                manual_brief, questions, reconcile)

FIXED = ServiceSpec.from_dict({
    "key": "1v1", "title": "1v1 Session", "type": "Training", "sport": "Soccer",
    "description": "One player, one hour.", "duration_minutes": 60,
    "pricing_mode": "fixed", "is_per_athlete": True,
    "tiers": [{"athletes": 1, "price": "85.00"}],
    "locations": ["Don Henderson Field"],
})

LIVE_RATE = {
    "id": 5, "title": "Soccer Training", "type": "Training",
    "duration_minutes": 60, "pricing_mode": "rate", "is_per_athlete": True,
    "price": {"mode": "rate", "from": "70.00", "from_hourly": "70.00"},
    "booking": {"mode": "calendar"},
}


class CatalogueQuestionTests(SimpleTestCase):
    """A gap report must be forwardable to a coach without editing."""

    def test_a_complete_service_asks_nothing_blocking(self):
        self.assertFalse([g for g in questions(FIXED) if g.is_blocking])

    def test_a_missing_price_blocks_and_asks_for_it(self):
        spec = ServiceSpec.from_dict({"title": "Block", "type": "Training",
                                      "sport": "Soccer", "duration_minutes": 60})
        gaps = questions(spec)
        self.assertTrue(any(g.is_blocking and g.field == "pricing_mode" for g in gaps))

    def test_blocking_questions_come_first(self):
        spec = ServiceSpec.from_dict({"title": "Thin", "sport": "Soccer"})
        severities = [g.severity for g in questions(spec)]
        self.assertEqual(severities, sorted(severities, key=lambda s: {
            "blocks": 0, "degrades": 1, "polish": 2}[s]))

    def test_a_missing_location_degrades_rather_than_blocks(self):
        spec = ServiceSpec.from_dict({**{
            "title": "1v1", "type": "Training", "sport": "Soccer",
            "duration_minutes": 60, "pricing_mode": "fixed", "is_per_athlete": True,
            "tiers": [{"athletes": 1, "price": "85.00"}]}})
        gaps = [g for g in questions(spec) if g.field == "locations"]
        self.assertEqual(gaps[0].severity, DEGRADES)
        self.assertIn("enquiry", gaps[0].what)

    def test_an_unknown_service_type_blocks(self):
        spec = ServiceSpec.from_dict({"title": "X", "type": "Bootcamp",
                                      "sport": "Soccer", "duration_minutes": 60,
                                      "pricing_mode": "fixed",
                                      "tiers": [{"athletes": 1, "price": "10"}]})
        self.assertTrue(any(g.is_blocking and g.field == "type" for g in questions(spec)))

    def test_rate_pricing_without_a_rate_blocks(self):
        spec = ServiceSpec.from_dict({"title": "X", "type": "Training",
                                      "sport": "Soccer", "duration_minutes": 60,
                                      "pricing_mode": "rate"})
        self.assertTrue(any(g.is_blocking and g.field == "hourly_rate"
                            for g in questions(spec)))

    def test_every_question_is_a_real_question(self):
        spec = ServiceSpec.from_dict({"title": "", "sport": ""})
        for gap in questions(spec):
            self.assertTrue(gap.question.strip().endswith("?") or
                            "?" in gap.question, gap.field)


class ReconcileTests(SimpleTestCase):

    def test_a_declared_service_absent_from_the_lab_is_missing(self):
        result = reconcile([FIXED], [])
        self.assertEqual([s.title for s in result.missing], ["1v1 Session"])
        self.assertFalse(result.is_clean)

    def test_a_service_in_the_lab_nobody_declared_is_extra(self):
        result = reconcile([], [LIVE_RATE])
        self.assertEqual([f["title"] for f in result.unexpected], ["Soccer Training"])

    def test_matching_titles_with_equal_terms_are_clean(self):
        spec = ServiceSpec.from_dict({
            "title": "Soccer Training", "type": "Training", "sport": "Soccer",
            "duration_minutes": 60, "pricing_mode": "rate",
            "is_per_athlete": True, "hourly_rate": "70.00",
            "locations": ["Don Henderson Field"]})
        result = reconcile([spec], [LIVE_RATE])
        self.assertEqual(len(result.matched), 1)
        self.assertTrue(result.is_clean)

    def test_a_price_that_drifted_is_reported_with_both_numbers(self):
        """The site quoting a different figure from the account is the whole
        failure this exists to catch."""
        spec = ServiceSpec.from_dict({
            "title": "Soccer Training", "type": "Training", "sport": "Soccer",
            "duration_minutes": 60, "pricing_mode": "rate",
            "is_per_athlete": True, "hourly_rate": "85.00",
            "locations": ["Don Henderson Field"]})
        result = reconcile([spec], [LIVE_RATE])
        self.assertEqual(len(result.drifted), 1)
        _, _, differences = result.drifted[0]
        self.assertTrue(any("85" in d and "70" in d for d in differences))

    def test_a_length_that_drifted_is_reported(self):
        spec = ServiceSpec.from_dict({
            "title": "Soccer Training", "type": "Training", "sport": "Soccer",
            "duration_minutes": 90, "pricing_mode": "rate",
            "is_per_athlete": True, "hourly_rate": "70.00",
            "locations": ["Don Henderson Field"]})
        _, _, differences = reconcile([spec], [LIVE_RATE]).drifted[0]
        self.assertTrue(any("90" in d and "60" in d for d in differences))

    def test_enquiry_only_in_the_lab_when_the_site_expects_a_calendar(self):
        enquiry = {**LIVE_RATE, "booking": {"mode": "enquiry", "reason": "no_location"}}
        spec = ServiceSpec.from_dict({
            "title": "Soccer Training", "type": "Training", "sport": "Soccer",
            "duration_minutes": 60, "pricing_mode": "rate",
            "is_per_athlete": True, "hourly_rate": "70.00",
            "locations": ["Don Henderson Field"]})
        _, _, differences = reconcile([spec], [enquiry]).drifted[0]
        self.assertTrue(any("enquiry-only" in d for d in differences))

    def test_titles_match_regardless_of_spacing_and_case(self):
        spec = ServiceSpec.from_dict({
            "title": "soccer   training", "type": "Training", "sport": "Soccer",
            "duration_minutes": 60, "pricing_mode": "rate",
            "is_per_athlete": True, "hourly_rate": "70.00",
            "locations": ["X"]})
        self.assertEqual(len(reconcile([spec], [LIVE_RATE]).matched), 1)


class BriefAndPayloadTests(SimpleTestCase):

    def test_the_brief_marks_what_is_unknown(self):
        spec = ServiceSpec.from_dict({"title": "Block", "sport": "Soccer"})
        text = "\n".join(manual_brief(spec))
        self.assertIn("— ASK —", text)

    def test_the_brief_names_every_tier(self):
        text = "\n".join(manual_brief(FIXED))
        self.assertIn("$85.00", text)
        self.assertIn("Don Henderson Field", text)

    def test_the_payload_mirrors_the_lab_models(self):
        payload = lab_payload(FIXED)
        self.assertEqual(payload["pricing_mode"], "fixed")
        self.assertEqual(payload["packages"][0]["athletes"], 1)
        self.assertEqual(payload["packages"][0]["price"], "85.00")

    def test_rate_mode_carries_an_hourly_rate_not_a_price(self):
        spec = ServiceSpec.from_dict({
            "title": "T", "type": "Training", "sport": "Soccer",
            "duration_minutes": 60, "pricing_mode": "rate",
            "is_per_athlete": True, "hourly_rate": "70.00"})
        package = lab_payload(spec)["packages"][0]
        self.assertEqual(package["hourly_rate"], "70.00")
        self.assertNotIn("price", package)


# ------------------------------------------------------------ prepaid blocks

from apps.lab.presenters import block_card, block_cards

BLOCK = {
    "id": 1, "title": "Six-Week Block",
    "description": "One session a week for six weeks.",
    "service": {"id": 1, "title": "1v1 Session"},
    "sessions": 6, "price": "459.00", "price_per_session": "76.50",
    "valid_weeks": 12,
    "saving": {"singles_total": "510.00", "amount": "51.00", "percent": 10},
    "purchase": {"mode": "enquiry", "reason": "no_checkout_yet"},
}


class BlockCardTests(SimpleTestCase):

    def test_a_block_reads_as_a_card(self):
        card = block_card(BLOCK)
        self.assertEqual(card.price_label, "$459")
        self.assertEqual(card.per_session_label, "$76.50")
        self.assertEqual(card.saving_label, "save $51 (10%)")
        self.assertEqual(card.window_label, "use within 12 weeks")

    def test_null_weeks_reads_as_never_not_zero(self):
        """Printing 'use within 0 weeks' from a null is the obvious way to get
        this wrong."""
        card = block_card({**BLOCK, "valid_weeks": None})
        self.assertEqual(card.window_label, "no expiry")
        self.assertNotIn("0", card.window_label)

    def test_a_block_with_no_saving_claims_none(self):
        card = block_card({**BLOCK, "saving": None})
        self.assertEqual(card.saving_label, "")

    def test_the_saving_is_never_recomputed_here(self):
        """The API already applied the coach's packages and floors. If this
        multiplied instead, it would contradict the tariff beside it."""
        card = block_card({**BLOCK,
                           "saving": {"singles_total": "999.00",
                                      "amount": "540.00", "percent": 54}})
        self.assertIn("54%", card.saving_label)   # the API's number, not ours

    def test_a_block_leads_to_an_enquiry_that_names_it(self):
        self.assertIn("block=1", block_card(BLOCK).url)


@override_settings(**SETTINGS)
class BlockStoreTests(TestCase):

    def test_blocks_come_back_as_cards(self):
        with mock.patch("urllib.request.urlopen",
                        return_value=_response({"blocks": [BLOCK]})):
            cards, notice = store.prepaid_blocks()
        self.assertEqual(len(cards), 1)
        self.assertIsNone(notice)

    def test_an_outage_yields_a_notice_and_no_prices(self):
        with mock.patch("urllib.request.urlopen",
                        side_effect=urllib.error.URLError("down")):
            cards, notice = store.prepaid_blocks()
        self.assertEqual(cards, [])
        self.assertTrue(notice)
        self.assertNotIn("$", notice)


from apps.lab.catalogue import (BlockSpec, block_manual_brief, block_questions,
                                reconcile_blocks)

BLOCK_SPEC = BlockSpec.from_dict({
    "key": "six-week-block", "title": "Six-Week Block",
    "service_key": "1v1-session", "sessions": 6, "price": "459.00",
    "valid_weeks": 12, "description": "Six weeks."})


class BlockSpecTests(SimpleTestCase):
    """A block is not a service, and describing it as one is why Six-Week
    Block could not be created before The LAB grew SessionBlock."""

    def test_a_complete_block_asks_nothing_blocking(self):
        self.assertFalse([g for g in block_questions(BLOCK_SPEC, ["1v1-session"])
                          if g.is_blocking])

    def test_a_block_must_point_at_a_service_that_exists(self):
        gaps = block_questions(BLOCK_SPEC, ["something-else"])
        self.assertTrue(any(g.is_blocking and g.field == "service_key" for g in gaps))

    def test_one_session_is_not_a_block(self):
        spec = BlockSpec.from_dict({**{"key": "x", "title": "X",
                                       "service_key": "1v1-session",
                                       "sessions": 1, "price": "80.00"}})
        self.assertTrue(any(g.is_blocking and g.field == "sessions"
                            for g in block_questions(spec, ["1v1-session"])))

    def test_a_missing_window_degrades_rather_than_blocks(self):
        spec = BlockSpec.from_dict({"key": "x", "title": "X",
                                    "service_key": "1v1-session",
                                    "sessions": 6, "price": "459.00"})
        gaps = [g for g in block_questions(spec, ["1v1-session"])
                if g.field == "valid_weeks"]
        self.assertEqual(gaps[0].severity, DEGRADES)

    def test_the_brief_says_no_expiry_rather_than_zero(self):
        spec = BlockSpec.from_dict({"key": "x", "title": "X",
                                    "service_key": "1v1-session",
                                    "sessions": 6, "price": "459.00"})
        self.assertIn("no expiry", "\n".join(block_manual_brief(spec)))


class BlockReconcileTests(SimpleTestCase):

    LIVE = {"id": 1, "title": "Six-Week Block", "sessions": 6,
            "price": "459.00", "valid_weeks": 12}

    def test_agreement_is_a_match(self):
        result = reconcile_blocks([BLOCK_SPEC], [self.LIVE])
        self.assertEqual(len(result.matched), 1)
        self.assertTrue(result.is_clean)

    def test_a_price_difference_is_reported_with_both_numbers(self):
        result = reconcile_blocks([BLOCK_SPEC], [{**self.LIVE, "price": "500.00"}])
        _, _, differences = result.drifted[0]
        self.assertTrue(any("459" in d and "500" in d for d in differences))

    def test_never_expires_is_not_compared_as_zero(self):
        """None on either side is a real answer, not a missing number."""
        spec = BlockSpec.from_dict({"key": "x", "title": "Six-Week Block",
                                    "service_key": "1v1-session", "sessions": 6,
                                    "price": "459.00", "valid_weeks": None})
        result = reconcile_blocks([spec], [{**self.LIVE, "valid_weeks": None}])
        self.assertEqual(len(result.matched), 1)

    def test_a_block_only_in_the_lab_is_extra(self):
        result = reconcile_blocks([], [self.LIVE])
        self.assertEqual(len(result.unexpected), 1)
