from django.contrib import admin

from .models import Capability, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "stage", "year", "is_featured", "is_live", "sort")
    list_editable = ("is_featured", "is_live", "sort")
    list_filter = ("stage", "is_live", "is_featured")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "tagline", "stack")


@admin.register(Capability)
class CapabilityAdmin(admin.ModelAdmin):
    list_display = ("title", "proof_project", "is_live", "sort")
    list_editable = ("is_live", "sort")
    search_fields = ("title", "blurb")
