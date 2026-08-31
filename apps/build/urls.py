from django.urls import path

from . import views

app_name = "build"

urlpatterns = [
    path("", views.index, name="index"),
    path("<slug:slug>/", views.project_detail, name="project_detail"),
]
