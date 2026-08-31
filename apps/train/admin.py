from django.contrib import admin, messages
from django.utils import timezone

from .models import Booking, Law, SessionType, Slot


@admin.register(Law)
class LawAdmin(admin.ModelAdmin):
    list_display = ("number", "title", "is_live")
    list_editable = ("is_live",)


@admin.register(SessionType)
class SessionTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "format", "duration_minutes", "capacity", "price_label", "is_live", "sort")
    list_editable = ("is_live", "sort")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("format", "is_live")


class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    fields = ("reference", "player_name", "email", "status")
    readonly_fields = ("reference",)
    show_change_link = True


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ("starts_at", "session_type", "location", "status", "seats_left")
    list_filter = ("status", "session_type", "location")
    date_hierarchy = "starts_at"
    inlines = [BookingInline]

    @admin.display(description="Seats left")
    def seats_left(self, obj):
        return obj.seats_left


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("reference", "player_name", "slot", "status", "created_at")
    list_filter = ("status", "slot__session_type")
    search_fields = ("reference", "player_name", "email", "phone")
    readonly_fields = ("reference", "created_at", "updated_at", "confirmed_at")
    date_hierarchy = "created_at"
    actions = ("confirm_bookings", "decline_bookings")

    @admin.action(description="Confirm selected bookings")
    def confirm_bookings(self, request, queryset):
        count = queryset.update(
            status=Booking.Status.CONFIRMED, confirmed_at=timezone.now()
        )
        self.message_user(request, f"{count} confirmed.", messages.SUCCESS)

    @admin.action(description="Decline selected bookings")
    def decline_bookings(self, request, queryset):
        count = queryset.update(status=Booking.Status.DECLINED)
        self.message_user(request, f"{count} declined.", messages.WARNING)
