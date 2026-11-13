from django.contrib import admin
from django.utils.html import format_html

from .models import Message, Notification, Offer, PlayerProfile, Thread


@admin.register(PlayerProfile)
class PlayerProfileAdmin(admin.ModelAdmin):
    list_display  = ("display_name", "email", "rating_badge", "club", "position", "grad_year", "rating_set_at")
    list_filter   = ("rating",)
    search_fields = ("user__username", "user__first_name", "user__last_name", "user__email", "club")
    readonly_fields = ("user", "rating_set_at", "created_at", "updated_at")
    fields = (
        "user", "rating", "rating_set_at",
        "notes",
        "club", "position", "grad_year",
        "created_at", "updated_at",
    )
    ordering = ("-rating", "user__last_name")

    def display_name(self, obj):
        return obj.display_name
    display_name.short_description = "Player"

    def email(self, obj):
        return obj.user.email
    email.short_description = "Email"

    def rating_badge(self, obj):
        colours = {0: "#555", 1: "#6b9", 2: "#5af", 3: "#fa0", 4: "#f72", 5: "#e33"}
        colour = colours.get(obj.rating, "#555")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:3px;font-size:11px">{}</span>',
            colour, obj.get_rating_display(),
        )
    rating_badge.short_description = "Rating"


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display  = ("title", "tier_label", "min_rating", "max_rating", "requires_auth", "is_live", "sort")
    list_filter   = ("is_live", "requires_auth")
    list_editable = ("is_live", "sort")
    search_fields = ("title", "body", "tier_label")
    fieldsets = (
        (None, {"fields": ("title", "body", "cta_label", "cta_url", "is_live", "sort")}),
        ("Targeting", {"fields": ("min_rating", "max_rating", "requires_auth", "tier_label")}),
    )


class MessageInline(admin.TabularInline):
    model  = Message
    extra  = 0
    readonly_fields = ("sender_type", "sender", "body", "is_ai_response", "is_escalation", "created_at")
    can_delete = False
    show_change_link = True
    fields = ("sender_type", "body", "is_ai_response", "is_escalation", "is_read_by_coach", "created_at")


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display  = ("reference", "player_name", "subject", "service_name", "status", "coach_unread", "message_count", "updated_at")
    list_filter   = ("status", "coach_unread")
    search_fields = ("reference", "player__username", "player__first_name", "player__last_name", "subject")
    readonly_fields = ("reference", "created_at", "updated_at")
    inlines = [MessageInline]
    ordering = ("-updated_at",)

    def player_name(self, obj):
        return obj.player.get_full_name() or obj.player.username
    player_name.short_description = "Player"

    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = "Messages"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display  = ("thread", "sender_type", "body_preview", "is_ai_response", "is_escalation", "created_at")
    list_filter   = ("sender_type", "is_ai_response", "is_escalation")
    search_fields = ("body", "thread__reference")
    readonly_fields = ("created_at", "updated_at")

    def body_preview(self, obj):
        return obj.body[:60]
    body_preview.short_description = "Body"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "title", "is_read", "created_at")
    list_filter  = ("kind", "is_read")
    search_fields = ("user__username", "title")
