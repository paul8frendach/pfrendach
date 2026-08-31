from django.test import TestCase
from django.urls import reverse

from apps.create.models import Package, Work
from apps.house.models import World


class CreateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        World.objects.create(
            slug="create", verb="Create", name="Vision Oasis", descriptor="d",
            headline="h", lead="l", card_line="c",
        )
        Work.objects.create(title="Night Session", slug="night-session", kind=Work.Kind.FILM, year="2026")
        Work.objects.create(title="Stills Set One", slug="stills-one", kind=Work.Kind.STILLS)
        Package.objects.create(
            name="Session Film", slug="session-film", summary="s",
            deliverables="60s edit\n3 cutdowns", price_from=450,
        )

    def test_index_lists_work_and_packages(self):
        response = self.client.get(reverse("create:index"))
        self.assertContains(response, "Night Session")
        self.assertContains(response, "Session Film")
        self.assertContains(response, "From $450")

    def test_kind_filter(self):
        response = self.client.get(reverse("create:index"), {"kind": "stills"})
        self.assertContains(response, "Stills Set One")
        self.assertNotContains(response, "Night Session")

    def test_package_deliverables_split_by_line(self):
        package = Package.objects.get(slug="session-film")
        self.assertEqual(package.deliverable_lines, ["60s edit", "3 cutdowns"])

    def test_work_detail_credits_vision_oasis(self):
        response = self.client.get(reverse("create:work_detail", args=["night-session"]))
        self.assertContains(response, "Vision Oasis")
