from django.urls import path

from . import views

app_name = "train"

urlpatterns = [
    path("", views.index, name="index"),
    path("schedule/", views.schedule, name="schedule"),
    # LAB-backed storefront. `service_detail` takes a LAB service id; the
    # slug route below still serves the local SessionType rows the booking
    # flow uses until availability and bookings move onto the API too.
    path("service/<int:service_id>/", views.service_detail, name="service_detail"),
    path("enquire/", views.enquire, name="enquire"),
    path("enquire/sent/", views.enquiry_sent, name="enquiry_sent"),
    path("sessions/<slug:slug>/", views.session_detail, name="session_detail"),
    path("book/<int:slot_id>/", views.book, name="book"),
    path("booking/<str:reference>/", views.booking_detail, name="booking_detail"),
    path("api/sessions/", views.api_sessions, name="api_sessions"),
    path("api/slots/", views.api_slots, name="api_slots"),
    path("api/bookings/<str:reference>/", views.api_booking, name="api_booking"),
]
