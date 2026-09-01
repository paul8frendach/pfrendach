import json
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.house.models import World
from apps.train.models import Booking, SessionType, Slot


class BookingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        World.objects.create(
            slug="train", verb="Train", name="FRENDACH", descriptor="Soccer training",
            headline="h", lead="l", card_line="c",
        )
        cls.session = SessionType.objects.create(
            name="1v1 Session", slug="1v1-session", summary="s",
            duration_minutes=60, capacity=1, price=85,
        )
        cls.slot = Slot.objects.create(
            session_type=cls.session,
            starts_at=timezone.now() + timedelta(days=3),
        )

    def payload(self, **overrides):
        data = {
            "player_name": "A Player",
            "email": "player@example.com",
            "goal": "First touch",
            "consent": "on",
        }
        data.update(overrides)
        return data

    def test_slot_inherits_capacity_from_its_session_type(self):
        session = SessionType.objects.create(
            name="Group", slug="group", summary="s", capacity=4
        )
        slot = Slot.objects.create(
            session_type=session, starts_at=timezone.now() + timedelta(days=4)
        )
        self.assertEqual(slot.capacity, 4)

    def test_booking_creates_a_pending_request_with_a_reference(self):
        response = self.client.post(
            reverse("train:book", args=[self.slot.pk]), self.payload(), follow=True
        )
        self.assertEqual(response.status_code, 200)
        booking = Booking.objects.get()
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertTrue(booking.reference.startswith("FR-"))
        self.assertContains(response, booking.reference)

    def test_a_full_slot_stops_being_bookable(self):
        self.client.post(reverse("train:book", args=[self.slot.pk]), self.payload())
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.seats_left, 0)
        self.assertFalse(self.slot.is_bookable)

        response = self.client.get(reverse("train:book", args=[self.slot.pk]))
        self.assertRedirects(response, reverse("train:schedule"))
        self.assertEqual(Booking.objects.count(), 1)

    def test_a_cancelled_booking_frees_the_seat(self):
        self.client.post(reverse("train:book", args=[self.slot.pk]), self.payload())
        booking = Booking.objects.get()
        booking.status = Booking.Status.CANCELLED
        booking.save()
        self.slot.refresh_from_db()
        self.assertTrue(self.slot.is_bookable)

    def test_past_slots_are_never_offered(self):
        Slot.objects.create(
            session_type=self.session, starts_at=timezone.now() - timedelta(days=1)
        )
        self.assertEqual(Slot.objects.open().count(), 1)

    def test_consent_is_required(self):
        response = self.client.post(
            reverse("train:book", args=[self.slot.pk]), self.payload(consent="")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Booking.objects.count(), 0)

    def test_booking_page_is_reachable_by_reference(self):
        self.client.post(reverse("train:book", args=[self.slot.pk]), self.payload())
        booking = Booking.objects.get()
        response = self.client.get(booking.get_absolute_url())
        self.assertContains(response, "Pending")

    def test_confirm_stamps_the_time(self):
        self.client.post(reverse("train:book", args=[self.slot.pk]), self.payload())
        booking = Booking.objects.get()
        booking.confirm()
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertIsNotNone(booking.confirmed_at)


class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.session = SessionType.objects.create(
            name="1v1 Session", slug="1v1-session", summary="s", capacity=1, price=85
        )
        cls.slot = Slot.objects.create(
            session_type=cls.session, starts_at=timezone.now() + timedelta(days=2)
        )

    def test_sessions_endpoint(self):
        data = json.loads(self.client.get(reverse("train:api_sessions")).content)
        self.assertEqual(data["sessions"][0]["slug"], "1v1-session")
        self.assertEqual(data["sessions"][0]["price_label"], "$85")

    def test_slots_endpoint_filters_by_session(self):
        data = json.loads(
            self.client.get(reverse("train:api_slots"), {"session": "1v1-session"}).content
        )
        self.assertEqual(len(data["slots"]), 1)
        self.assertEqual(data["slots"][0]["seats_left"], 1)

        empty = json.loads(
            self.client.get(reverse("train:api_slots"), {"session": "nope"}).content
        )
        self.assertEqual(empty["slots"], [])

    def test_booking_endpoint_404s_on_a_bad_reference(self):
        response = self.client.get(reverse("train:api_booking", args=["FR-XXXXXX"]))
        self.assertEqual(response.status_code, 404)


# --------------------------------------------------------------- LAB wrapper

import io
import urllib.error
from unittest import mock

from django.test import override_settings

LAB_SETTINGS = dict(LAB_API_BASE="http://lab.test", LAB_API_KEY="lab_test_x",
                    LAB_CACHE_SECONDS=0)

LAB_SERVICES = {"services": [
    {"id": 1, "title": "1v1 Session", "type": "Training",
     "description": "One player, one hour.", "duration_minutes": 60,
     "is_per_athlete": True, "max_athletes": 1,
     "price": {"mode": "fixed", "from": "85.00", "to": None},
     "booking": {"mode": "enquiry", "reason": "no_location"}, "durations": []},
    {"id": 4, "title": "Six-Week Block", "type": "Training",
     "description": "Six weeks.", "duration_minutes": 60,
     "is_per_athlete": True, "max_athletes": None, "price": None,
     "booking": {"mode": "enquiry", "reason": "no_packages"}, "durations": []},
]}

LAB_INTAKE = {
    "is_enabled": True, "cta_text": "Start training",
    "collect": {"athlete_name": True, "parent_name": True, "email": True,
                "phone": True, "age": True, "experience": True, "notes": True},
    "fields": [{"id": 1, "label": "Position", "type": "short_text",
                "required": False, "per_athlete": True, "options": []}],
}


def _json_response(body):
    fake = mock.MagicMock()
    fake.read.return_value = json.dumps(body).encode()
    fake.status = 200
    fake.__enter__.return_value = fake
    fake.__exit__.return_value = False
    return fake


def _route(request, timeout=None):
    """Answer by path, so one patch serves a whole page render."""
    url = request.full_url if hasattr(request, "full_url") else request.get_full_url()
    if "/services" in url:
        return _json_response(LAB_SERVICES)
    if "/intake-form" in url:
        return _json_response(LAB_INTAKE)
    if "/leads" in url:
        return _json_response({"lead_id": 77, "status": "new", "source": "api:test"})
    return _json_response({})


@override_settings(**LAB_SETTINGS)
class TrainStorefrontTests(TestCase):
    """The tariff is The LAB's answer, or an honest silence."""

    @classmethod
    def setUpTestData(cls):
        World.objects.create(
            slug="train", verb="Train", name="FRENDACH", descriptor="Soccer training",
            headline="h", lead="l", card_line="c",
        )

    def test_index_prints_lab_prices(self):
        with mock.patch("urllib.request.urlopen", side_effect=_route):
            response = self.client.get(reverse("train:index"))
        self.assertContains(response, "1v1 Session")
        self.assertContains(response, "$85")
        self.assertContains(response, "On request")   # the priceless one

    def test_index_survives_a_lab_outage_without_inventing_a_price(self):
        with mock.patch("urllib.request.urlopen",
                        side_effect=urllib.error.URLError("down")):
            response = self.client.get(reverse("train:index"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "$85")
        self.assertContains(response, "Ask directly")

    def test_service_detail_reads_from_the_api(self):
        with mock.patch("urllib.request.urlopen", side_effect=_route):
            response = self.client.get(reverse("train:service_detail", args=[1]))
        self.assertContains(response, "1v1 Session")
        self.assertContains(response, "60 minutes")

    def test_unknown_service_is_404_only_when_the_lab_answered(self):
        with mock.patch("urllib.request.urlopen", side_effect=_route):
            response = self.client.get(reverse("train:service_detail", args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_outage_shows_the_room_rather_than_a_404(self):
        with mock.patch("urllib.request.urlopen",
                        side_effect=urllib.error.URLError("down")):
            response = self.client.get(reverse("train:service_detail", args=[999]))
        self.assertEqual(response.status_code, 200)


@override_settings(**LAB_SETTINGS)
class EnquiryTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        World.objects.create(
            slug="train", verb="Train", name="FRENDACH", descriptor="Soccer training",
            headline="h", lead="l", card_line="c",
        )

    def test_form_is_built_from_the_coachs_own_config(self):
        with mock.patch("urllib.request.urlopen", side_effect=_route):
            response = self.client.get(reverse("train:enquire"))
        self.assertContains(response, "Position")
        self.assertContains(response, 'name="athlete_0_custom_1"')

    def test_add_another_player_needs_no_javascript(self):
        with mock.patch("urllib.request.urlopen", side_effect=_route):
            response = self.client.post(reverse("train:enquire"), {
                "athlete_count": "1", "add_athlete": "1",
                "payer_first_name": "Dana",
            })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="athlete_1_first_name"')
        self.assertContains(response, 'value="Dana"')      # kept what was typed

    def test_add_another_player_does_not_submit(self):
        posted = []
        def spy(request, timeout=None):
            posted.append(request.get_full_url())
            return _route(request, timeout)
        with mock.patch("urllib.request.urlopen", side_effect=spy):
            self.client.post(reverse("train:enquire"),
                             {"athlete_count": "1", "add_athlete": "1"})
        self.assertFalse([u for u in posted if u.endswith("/leads")])

    def test_a_good_submission_reaches_the_lab(self):
        sent = {}
        def spy(request, timeout=None):
            if request.get_full_url().endswith("/leads"):
                sent["body"] = json.loads(request.data.decode())
                sent["idem"] = request.get_header("Idempotency-key")
            return _route(request, timeout)
        with mock.patch("urllib.request.urlopen", side_effect=spy):
            response = self.client.post(reverse("train:enquire"), {
                "athlete_count": "1",
                "payer_first_name": "Dana", "payer_last_name": "Ruiz",
                "payer_email": "dana@example.com", "payer_phone": "4105550188",
                "athlete_0_first_name": "Mia", "athlete_0_last_name": "Ruiz",
                "athlete_0_age_type": "year", "athlete_0_birth_year": "2010",
                "athlete_0_custom_1": "Winger",
                "notes": "Weekends best.",
            })
        self.assertRedirects(response, reverse("train:enquiry_sent"))
        self.assertEqual(sent["body"]["payer"]["email"], "dana@example.com")
        self.assertEqual(sent["body"]["athletes"][0]["birth_year"], "2010")
        self.assertEqual(sent["body"]["athletes"][0]["answers"]["Position"], "Winger")
        self.assertTrue(sent["idem"])

    def test_the_service_they_came_from_is_named_in_the_notes(self):
        sent = {}
        def spy(request, timeout=None):
            if request.get_full_url().endswith("/leads"):
                sent["body"] = json.loads(request.data.decode())
            return _route(request, timeout)
        with mock.patch("urllib.request.urlopen", side_effect=spy):
            self.client.post(reverse("train:enquire"), {
                "athlete_count": "1", "service": "1",
                "payer_first_name": "D", "payer_last_name": "R",
                "payer_email": "d@e.com", "athlete_0_first_name": "Mia",
            })
        self.assertIn("1v1 Session", sent["body"]["notes"])

    def test_a_rejection_keeps_what_they_typed(self):
        def refuse(request, timeout=None):
            if request.get_full_url().endswith("/leads"):
                body = json.dumps({"error": {
                    "code": "email_belongs_to_account",
                    "message": "That email belongs to an existing LAB account.",
                }}).encode()
                raise urllib.error.HTTPError(
                    request.get_full_url(), 409, "conflict", {}, io.BytesIO(body))
            return _route(request, timeout)
        with mock.patch("urllib.request.urlopen", side_effect=refuse):
            response = self.client.post(reverse("train:enquire"), {
                "athlete_count": "1",
                "payer_first_name": "Dana", "payer_last_name": "Ruiz",
                "payer_email": "taken@example.com",
                "athlete_0_first_name": "Mia",
            })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "existing LAB account")
        self.assertContains(response, "taken@example.com")

    def test_a_disabled_form_is_explained_not_broken(self):
        def closed(request, timeout=None):
            if "/intake-form" in request.get_full_url():
                return _json_response({"is_enabled": False})
            return _route(request, timeout)
        with mock.patch("urllib.request.urlopen", side_effect=closed):
            response = self.client.get(reverse("train:enquire"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ask directly")
