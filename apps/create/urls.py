from django.urls import path

from . import views

app_name = "create"

urlpatterns = [
    path("", views.index, name="index"),
    path("request/", views.request_film, name="request"),
    path("request/thanks/", views.request_thanks, name="request_thanks"),
    path("<slug:slug>/", views.work_detail, name="work_detail"),
]
