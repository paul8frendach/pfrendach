"""FindThe90 Shop — Django admin registration."""

from django.contrib import admin

from .models import PrintfulProduct, PrintfulWebhookLog


@admin.register(PrintfulProduct)
class PrintfulProductAdmin(admin.ModelAdmin):
    list_display = ("display_name", "sync_product_id", "slug", "is_live", "sort")
    list_editable = ("is_live", "sort")
    prepopulated_fields = {"slug": ("display_name",)}
    search_fields = ("display_name", "slug")
    ordering = ("sort", "display_name")


@admin.register(PrintfulWebhookLog)
class PrintfulWebhookLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "event_type", "printful_order_id", "processed")
    list_filter = ("event_type", "processed")
    search_fields = ("printful_order_id",)
    readonly_fields = ("created_at", "updated_at", "event_type", "printful_order_id", "raw_payload", "processed", "notes")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False  # logs are append-only

    def has_delete_permission(self, request, obj=None):
        return False  # audit trail — never delete
