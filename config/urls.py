from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView

from apps.house.sitemaps import SITEMAPS

urlpatterns = [
    path("admin/", admin.site.urls),
    path("train/", include("apps.train.urls")),
    path("create/", include("apps.create.urls")),
    path("build/", include("apps.build.urls")),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": SITEMAPS},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots",
    ),
    path("", include("apps.house.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Paul Frendach — house"
admin.site.site_title = "PF house"
admin.site.index_title = "Create · Build · Train"
