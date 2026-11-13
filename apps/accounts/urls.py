from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Auth
    path("login/",  views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup,      name="signup"),

    # Player dashboard
    path("dashboard/",               views.dashboard,  name="dashboard"),

    # Player messaging
    path("messages/",                views.inbox,      name="inbox"),
    path("messages/compose/",        views.compose,    name="compose"),
    path("messages/<str:reference>/", views.thread_view, name="thread"),

    # Notification API
    path("notifications/count/",          views.notif_count,     name="notif_count"),
    path("notifications/<int:pk>/read/",  views.notif_mark_read, name="notif_mark_read"),

    # Coach dashboard
    path("coach/",                             views.coach_dashboard,   name="coach_dashboard"),
    path("coach/players/",                     views.coach_players,     name="coach_players"),
    path("coach/players/<int:pk>/rate/",       views.coach_rate_player, name="coach_rate_player"),
    path("coach/offers/",                      views.coach_offers,      name="coach_offers"),
    path("coach/offers/new/",                  views.coach_offer_form,  name="coach_offer_new"),
    path("coach/offers/<int:pk>/edit/",        views.coach_offer_form,  name="coach_offer_edit"),
    path("coach/offers/<int:pk>/toggle/",      views.coach_offer_toggle, name="coach_offer_toggle"),
    path("coach/inbox/",                       views.coach_inbox,       name="coach_inbox"),
    path("coach/inbox/<str:reference>/",       views.coach_thread,      name="coach_thread"),
]
