import os

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.house.mail import send_templated
from apps.house.models import SiteConfig

from .forms import CommissionForm
from .models import Commission, Method, Package, Work

# Where OMV commission requests are emailed. Its own inbox, not the house one.
OMV_NOTIFY_EMAIL = os.environ.get("OMV_NOTIFY_EMAIL", "paul@oasismediavisions.com")


def _grouped_work():
    """Live work bucketed by market category, newest first in each bucket."""
    live = Work.objects.filter(is_live=True)
    groups = []
    for value, label in Work.Category.choices:
        pieces = [w for w in live if w.category == value]
        if pieces:
            groups.append({"value": value, "label": label, "pieces": pieces})
    return groups


def index(request):
    category = request.GET.get("category")
    work = Work.objects.filter(is_live=True)
    if category in dict(Work.Category.choices):
        work = work.filter(category=category)
    featured = Work.objects.filter(is_live=True, is_featured=True)[:1].first()
    return render(
        request,
        "create/index.html",
        {
            "work": work,
            "featured": featured,
            "groups": _grouped_work(),
            "categories": Work.Category.choices,
            "active_category": category,
            "packages": Package.objects.filter(is_live=True),
            "methods": Method.objects.filter(is_live=True),
        },
    )


def work_detail(request, slug):
    piece = get_object_or_404(Work, slug=slug, is_live=True)
    return render(
        request,
        "create/work_detail.html",
        {
            "piece": piece,
            "more": Work.objects.filter(is_live=True, category=piece.category)
            .exclude(pk=piece.pk)[:3],
        },
    )


def request_film(request):
    """The professional service-request page. Pre-fills service / package from the URL."""
    service = request.GET.get("service")
    package = None
    package_slug = request.GET.get("package")
    if package_slug:
        package = Package.objects.filter(slug=package_slug, is_live=True).first()
        if package and not service:
            service = package.slug.split("-")[0]

    if request.method == "POST":
        form = CommissionForm(request.POST, service=service, package=package)
        if form.is_valid():
            commission = form.save(commit=False)
            commission.source_path = request.META.get("HTTP_REFERER", "")[:200]
            commission.save()
            site = SiteConfig.load()
            send_templated(
                subject=f"OMV commission — {commission.get_service_display()} · {commission.name}",
                template="commission_received",
                context={"commission": commission, "site": site},
                to=[OMV_NOTIFY_EMAIL],
            )
            messages.success(
                request,
                "Received. Paul reads every one of these himself — expect a real reply, not a robot.",
            )
            return redirect("create:request_thanks")
    else:
        form = CommissionForm(service=service, package=package)

    return render(
        request,
        "create/request.html",
        {
            "form": form,
            "packages": Package.objects.filter(is_live=True),
            "selected_package": package,
        },
    )


def request_thanks(request):
    return render(request, "create/request_thanks.html")
