from django.urls import path

from . import views

app_name = "house"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("contact/thanks/", views.contact_thanks, name="contact_thanks"),
    path("flash/", views.flash, name="flash"),
]
