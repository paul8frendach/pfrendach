import re
from pathlib import Path
from django.conf import settings
from django.test import SimpleTestCase, TestCase
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


class SeamlessNavigationTests(TestCase):
    """The router swaps [data-main] only. If that contract breaks, navigation
    silently falls back to full reloads and the background restarts."""

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

    def test_every_page_exposes_a_swappable_main_and_a_world(self):
        for name in ["house:home", "house:about", "house:contact", "train:index",
                     "train:schedule", "create:index", "build:index"]:
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertContains(response, "data-main")
                self.assertContains(response, 'data-world="')

    def test_the_ground_is_mounted_once_outside_main(self):
        html = self.client.get(reverse("house:home")).content.decode()
        self.assertEqual(html.count("data-ground"), 1)
        self.assertLess(html.index("data-ground"), html.index("data-main"))

    def test_train_type_kit_is_loaded_globally_not_per_page(self):
        # Loading it per page would make a room swap fetch fonts mid-transition.
        for name in ["house:home", "build:index", "train:index"]:
            with self.subTest(page=name):
                self.assertContains(self.client.get(reverse(name)), "family=Anton")


class ChromeContractTests(TestCase):
    """The chrome is fixed, so its expanded height has to be held in the flow by
    a spacer. Without that, collapsing the bar changes the document height,
    which shifts the scroll, which re-runs the collapse — the judder."""

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

    def test_fixed_chrome_always_ships_its_spacer(self):
        for name in ["house:home", "train:index", "create:index", "build:index", "house:contact"]:
            with self.subTest(page=name):
                self.assertContains(self.client.get(reverse(name)), "chrome__spacer")

    def test_signature_appears_twice_for_the_crossfade(self):
        # Crest and mini. One collapses, the other fades in; neither moves.
        html = self.client.get(reverse("house:home")).content.decode()
        self.assertIn("sig--crest", html)
        self.assertIn("sig--mini", html)
        self.assertEqual(html.count("marks/pf-house.svg"), 4)  # crest, mini, footer, favicon

    def test_about_and_contact_are_furniture_not_worlds(self):
        html = self.client.get(reverse("house:home")).content.decode()
        # They live in the subnav, never in the tab rail.
        subnav = html[html.index('class="subnav"'):html.index("</nav>", html.index('class="subnav"'))]
        self.assertIn("About", subnav)
        self.assertIn("Contact", subnav)
        tabs = html[html.index('class="tabs"'):html.index("</nav>", html.index('class="tabs"'))]
        self.assertNotIn("About", tabs)
        self.assertNotIn("Contact", tabs)


class AlignmentContractTests(TestCase):
    """Rows of peers must never wrap into a ragged stack. The templates hold up
    their end by not hard-coding alignment that a narrow screen cannot undo."""

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

    def test_no_inline_text_align_right_survives_into_a_stack(self):
        # An inline right-align cannot be undone by a media query, so a stacked
        # row would keep it and read as broken. Use a class instead.
        for name in ["house:home", "train:index", "create:index", "build:index"]:
            with self.subTest(page=name):
                html = self.client.get(reverse(name)).content.decode()
                self.assertNotIn("text-align:right", html.replace(" ", ""))

    def test_button_rows_are_marked_as_peer_groups(self):
        # .actions carries the equal-width rule; loose buttons would escape it.
        html = self.client.get(reverse("train:index")).content.decode()
        self.assertIn('class="actions"', html)


class SignatureWashTests(SimpleTestCase):
    """The light behind the signature — and the two rules that keep it light.

    This wash failed twice before it worked, both times rendering as a grey
    plate behind the wordmark rather than as light. Neither failure was a taste
    problem; both were geometry, and both are the kind that come back the
    moment somebody nudges a number. So they are asserted here rather than
    left in a comment.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        css = Path(settings.BASE_DIR) / "static" / "css" / "house.css"
        cls.css = css.read_text()
        start = cls.css.index(".chrome .sig::before {")
        cls.rule = cls.css[start:cls.css.index("}", start)]

    def test_the_wash_exists_behind_the_chrome_signature(self):
        self.assertIn(".chrome .sig::before", self.css)
        self.assertIn("z-index: -1", self.rule)

    def test_it_never_bleeds_vertically(self):
        """`.chrome__crest` is overflow:hidden and is exactly the signature's
        height — measured, zero pixels above or below. Any vertical inset is
        therefore clipped into a hard rectangle, which is what made the first
        two attempts look like a plate."""
        inset = [t for t in self.rule.splitlines() if "inset:" in t][0]
        top, right, bottom, left = inset.split("inset:")[1].strip(" ;").split()
        self.assertEqual(top, "0", "vertical bleed is clipped by .chrome__crest")
        self.assertEqual(bottom, "0", "vertical bleed is clipped by .chrome__crest")
        self.assertTrue(right.startswith("-") and left.startswith("-"),
                        "horizontally there IS room, and the wash should use it")

    def test_the_gradient_fades_out_before_its_own_edges(self):
        """A radial still coloured where its box ends draws the same rectangle
        by a different route. With the colour gone by 72% of the radius,
        0.72 * r must stay inside the distance from the centre to each edge."""
        match = re.search(
            r"radial-gradient\(ellipse (\d+)% (\d+)% at (\d+)% (\d+)%.*?transparent (\d+)%",
            self.rule, re.S)
        self.assertIsNotNone(match, "the wash should be one sized ellipse")
        rx, ry, cx, cy, stop = (int(g) / 100 for g in match.groups())
        self.assertLess(stop * rx, cx, "colour still present at the left edge")
        self.assertLess(stop * rx, 1 - cx, "colour still present at the right edge")
        self.assertLess(stop * ry, cy, "colour still present at the top edge")
        self.assertLess(stop * ry, 1 - cy, "colour still present at the bottom edge")

    def test_the_colour_is_the_room_and_is_never_named(self):
        """Per-page colour comes from --accent, which every room already sets —
        so the wash, the ground and the clock change together. Naming gold,
        glow or steel here would fork the palette and, worse, edge towards
        colouring the mark per world, which the pack forbids."""
        self.assertIn("var(--accent)", self.rule)
        for locked in ("--gold", "--glow", "--steel", "#e8c36a", "#c6e04a", "#8fb4c4"):
            self.assertNotIn(locked, self.rule)

    def test_the_mark_itself_is_never_touched(self):
        """The wash sits behind the lockup. The moment it becomes a filter,
        a background or a tint ON the mark, the pack's rule is broken."""
        img_rules = re.findall(r"\.sig img \{(.*?)\}", self.css, re.S)
        for body in img_rules:
            self.assertNotIn("filter", body)
            self.assertNotIn("background", body)

    def test_it_is_scoped_to_the_chrome(self):
        """The splash signature and the footer one sit on their own grounds and
        do not want a second light source."""
        self.assertNotIn("\n.sig::before", self.css)
