from django.contrib import admin

from .models import Capability, Feature, Project


class FeatureInline(admin.TabularInline):
    model = Feature
    extra = 0
    fields = ("title", "blurb", "metric", "sort", "is_live")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "stage", "year", "is_featured", "is_live", "sort")
    list_editable = ("is_featured", "is_live", "sort")
    list_filter = ("stage", "is_live", "is_featured")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "tagline", "stack")
    inlines = [FeatureInline]


@admin.register(Capability)
class CapabilityAdmin(admin.ModelAdmin):
    list_display = ("title", "proof_project", "is_live", "sort")
    list_editable = ("is_live", "sort")
    search_fields = ("title", "blurb")


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "metric", "is_live", "sort")
    list_editable = ("is_live", "sort")
    list_filter = ("project",)
