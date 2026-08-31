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
