from django.test import TestCase
from django.urls import reverse

from apps.build.models import Capability, Project
from apps.house.models import World


class BuildTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        World.objects.create(
            slug="build", verb="Build", name="Web", descriptor="d",
            headline="h", lead="l", card_line="c",
        )
        cls.project = Project.objects.create(
            name="A Site", slug="a-site", tagline="t",
            stack="Django, Postgres, ffmpeg", year="2026", is_featured=True,
        )
        Capability.objects.create(title="Booking", blurb="b", proof_project=cls.project)

    def test_index_lists_projects_and_capabilities(self):
        response = self.client.get(reverse("build:index"))
        self.assertContains(response, "A Site")
        self.assertContains(response, "Booking")

    def test_stack_splits_into_chips(self):
        self.assertEqual(self.project.stack_items, ["Django", "Postgres", "ffmpeg"])

    def test_unpublished_projects_are_hidden(self):
        Project.objects.create(name="Draft", slug="draft", tagline="t", is_live=False)
        response = self.client.get(reverse("build:index"))
        self.assertNotContains(response, "Draft")
        self.assertEqual(self.client.get("/build/draft/").status_code, 404)


class FeatureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        World.objects.create(
            slug="build", verb="Build", name="Web", descriptor="d",
            headline="h", lead="l", card_line="c",
        )
        cls.project = Project.objects.create(name="An App", slug="an-app", tagline="t")

    def test_rack_shows_a_project_and_its_live_features(self):
        from apps.build.models import Feature

        Feature.objects.create(project=self.project, title="Booking", blurb="b", metric="3 endpoints")
        Feature.objects.create(project=self.project, title="Draft feature", blurb="b", is_live=False)
        response = self.client.get(reverse("build:index"))
        self.assertContains(response, "Booking")
        self.assertContains(response, "3 endpoints")
        self.assertNotContains(response, "Draft feature")
