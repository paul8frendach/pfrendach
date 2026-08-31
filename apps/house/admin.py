from django.contrib import admin

from .models import Inquiry, Milestone, SiteConfig, World


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Hero", {"fields": ("kicker", "headline", "lead", "show_intro_sting")}),
        ("House", {"fields": ("contact_email", "location", "footer_line", "booking_note")}),
        ("Elsewhere", {"fields": ("instagram_url", "youtube_url", "github_url")}),
    )

    def has_add_permission(self, request):
        return not SiteConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(World)
class WorldAdmin(admin.ModelAdmin):
    list_display = ("verb", "name", "slug", "is_live", "sort")
    list_editable = ("is_live", "sort")
    prepopulated_fields = {}


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ("title", "year", "confirmed", "is_live", "sort")
    list_editable = ("confirmed", "is_live", "sort")
    list_filter = ("confirmed", "is_live")
    search_fields = ("title", "detail")


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "world", "subject", "status", "created_at")
    list_filter = ("status", "world")
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("created_at", "updated_at", "source_path")
    date_hierarchy = "created_at"
