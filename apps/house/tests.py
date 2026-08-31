from django.test import TestCase
from django.urls import reverse

from apps.house.models import Inquiry, Milestone, SiteConfig, World


class HousePagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for slug, verb, name in [
            ("create", "Create", "Vision Oasis"),
            ("build", "Build", "Web"),
            ("train", "Train", "FRENDACH"),
        ]:
            World.objects.create(
                slug=slug, verb=verb, name=name, descriptor="x",
                headline="h", lead="l", card_line="c",
            )

    def test_home_renders_with_all_three_doors(self):
        response = self.client.get(reverse("house:home"))
        self.assertEqual(response.status_code, 200)
        for verb in ("Create", "Build", "Train"):
            self.assertContains(response, verb)

    def test_every_page_carries_the_same_house_mark(self):
        """The mark never changes between rooms. This is the one thing that must not drift."""
        for name in ["house:home", "house:about", "house:contact", "train:index",
                     "create:index", "build:index"]:
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "marks/pf-house.svg")
                self.assertContains(response, ">RENDACH<")

    def test_world_pages_declare_their_own_data_world(self):
        for slug in ("create", "build", "train"):
            with self.subTest(world=slug):
                response = self.client.get(reverse(f"{slug}:index"))
                self.assertContains(response, f'data-world="{slug}"')

    def test_about_prints_confirmed_milestones_only(self):
        Milestone.objects.create(title="Temple", detail="Captain", confirmed=True)
        Milestone.objects.create(title="Unconfirmed honour", confirmed=False)
        response = self.client.get(reverse("house:about"))
        self.assertContains(response, "Temple")
        self.assertNotContains(response, "Unconfirmed honour")

    def test_contact_form_creates_an_inquiry(self):
        response = self.client.post(
            reverse("house:contact"),
            {"name": "A Client", "email": "a@example.com", "message": "Build me a page."},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Inquiry.objects.count(), 1)

    def test_contact_form_rejects_the_honeypot(self):
        self.client.post(
            reverse("house:contact"),
            {"name": "Bot", "email": "b@example.com", "message": "spam", "company": "bot inc"},
        )
        self.assertEqual(Inquiry.objects.count(), 0)

    def test_site_config_is_a_singleton(self):
        first = SiteConfig.load()
        SiteConfig.objects.create(headline="Second")
        self.assertEqual(SiteConfig.objects.count(), 1)
        self.assertEqual(SiteConfig.load().pk, first.pk)

    def test_robots_and_sitemap(self):
        self.assertEqual(self.client.get("/robots.txt").status_code, 200)
        self.assertEqual(self.client.get("/sitemap.xml").status_code, 200)
