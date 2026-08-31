from django.contrib import admin

from .models import Package, Work


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "year", "is_featured", "is_live", "sort")
    list_editable = ("is_featured", "is_live", "sort")
    list_filter = ("kind", "is_live", "is_featured")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "client", "blurb")


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("name", "price_label", "turnaround", "is_live", "sort")
    list_editable = ("is_live", "sort")
    prepopulated_fields = {"slug": ("name",)}
