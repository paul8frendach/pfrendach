from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.build.models import Capability, Project
from apps.create.models import Work
from apps.train.models import Law, SessionType, Slot

from .forms import InquiryForm
from .mail import send_templated
from .models import Milestone, SiteConfig, World


def home(request):
    """The landing page: sting, three doors, a slice of each room."""
    return render(
        request,
        "house/home.html",
        {
            "featured_work": Work.objects.filter(is_live=True, is_featured=True)[:3],
            "featured_projects": Project.objects.filter(is_live=True, is_featured=True)[:3],
            "sessions": SessionType.objects.filter(is_live=True)[:3],
            "next_slots": Slot.objects.open().select_related("session_type")[:3],
            "laws": Law.objects.filter(is_live=True)[:3],
        },
    )


def about(request):
    return render(
        request,
        "house/about.html",
        {
            "milestones": Milestone.objects.filter(is_live=True, confirmed=True),
            "capabilities": Capability.objects.filter(is_live=True)[:4],
        },
    )


@require_http_methods(["GET", "POST"])
def contact(request):
    world = None
    world_slug = request.GET.get("world")
    if world_slug:
        world = World.objects.filter(slug=world_slug, is_live=True).first()

    if request.method == "POST":
        form = InquiryForm(request.POST, world=world)
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.source_path = request.META.get("HTTP_REFERER", "")[:200]
            inquiry.save()
            send_templated(
                subject=f"Inquiry — {inquiry.name}",
                template="inquiry_received",
                context={"inquiry": inquiry, "site": SiteConfig.load()},
                to=[SiteConfig.load().contact_email],
            )
            messages.success(
                request, "Received. You will hear back from Paul, not from a robot."
            )
            return redirect("house:contact_thanks")
    else:
        form = InquiryForm(world=world)

    return render(request, "house/contact.html", {"form": form, "picked_world": world})


def contact_thanks(request):
    return render(request, "house/contact_thanks.html")


def flash(request):
    """The sting on its own, for overlays and screen recordings. ?v=intro|outro"""
    variant = request.GET.get("v", "intro")
    if variant not in {"intro", "outro"}:
        variant = "intro"
    return render(request, "house/flash.html", {"variant": variant})
