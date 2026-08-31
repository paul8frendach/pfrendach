from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.build.models import Project
from apps.create.models import Work
from apps.train.models import SessionType


class StaticSitemap(Sitemap):
    changefreq = "monthly"
    priority = 1.0

    def items(self):
        return [
            "house:home",
            "house:about",
            "house:contact",
            "train:index",
            "train:schedule",
            "create:index",
            "build:index",
        ]

    def location(self, item):
        return reverse(item)


class ModelSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7
    model = None

    def items(self):
        return self.model.objects.filter(is_live=True)

    def lastmod(self, obj):
        return obj.updated_at


class WorkSitemap(ModelSitemap):
    model = Work


class ProjectSitemap(ModelSitemap):
    model = Project


class SessionSitemap(ModelSitemap):
    model = SessionType


SITEMAPS = {
    "static": StaticSitemap,
    "work": WorkSitemap,
    "projects": ProjectSitemap,
    "sessions": SessionSitemap,
}
