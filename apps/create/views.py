from django.shortcuts import get_object_or_404, render

from .models import Package, Work


def index(request):
    kind = request.GET.get("kind")
    work = Work.objects.filter(is_live=True)
    if kind in dict(Work.Kind.choices):
        work = work.filter(kind=kind)
    return render(
        request,
        "create/index.html",
        {
            "work": work,
            "kinds": Work.Kind.choices,
            "active_kind": kind,
            "packages": Package.objects.filter(is_live=True),
        },
    )


def work_detail(request, slug):
    piece = get_object_or_404(Work, slug=slug, is_live=True)
    return render(
        request,
        "create/work_detail.html",
        {
            "piece": piece,
            "more": Work.objects.filter(is_live=True).exclude(pk=piece.pk)[:3],
        },
    )
