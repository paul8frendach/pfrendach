from django.contrib import admin

from .models import Commission, Method, Package, Work


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "kind", "year", "is_featured", "is_live", "sort")
    list_editable = ("category", "is_featured", "is_live", "sort")
    list_filter = ("category", "kind", "is_live", "is_featured")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "client", "location", "blurb")


@admin.register(Method)
class MethodAdmin(admin.ModelAdmin):
    list_display = ("name", "kicker", "is_live", "sort")
    list_editable = ("is_live", "sort")


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("name", "price_label", "turnaround", "is_featured", "is_live", "sort")
    list_editable = ("is_featured", "is_live", "sort")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ("name", "service", "event_date", "location", "status", "created_at")
    list_editable = ("status",)
    list_filter = ("status", "service", "notified_oasis")
    search_fields = ("name", "email", "location", "details")
    readonly_fields = ("created_at", "updated_at", "source_path")
    date_hierarchy = "created_at"
    fieldsets = (
        (None, {"fields": ("name", "email", "phone", "how_heard")}),
        ("The job", {"fields": ("service", "package", "event_date", "location", "budget", "details")}),
        ("Tracking", {"fields": ("status", "notified_oasis", "source_path", "created_at", "updated_at")}),
    )
