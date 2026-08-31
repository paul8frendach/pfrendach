from django.shortcuts import get_object_or_404, render

from .models import Capability, Project


def index(request):
    return render(
        request,
        "build/index.html",
        {
            "projects": Project.objects.filter(is_live=True).prefetch_related("features"),
            "capabilities": Capability.objects.filter(is_live=True),
        },
    )


def project_detail(request, slug):
    project = get_object_or_404(Project, slug=slug, is_live=True)
    return render(
        request,
        "build/project_detail.html",
        {
            "project": project,
            "more": Project.objects.filter(is_live=True).exclude(pk=project.pk)[:3],
        },
    )
