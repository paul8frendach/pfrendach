from django.urls import path

from . import views

app_name = "create"

urlpatterns = [
    path("", views.index, name="index"),
    path("<slug:slug>/", views.work_detail, name="work_detail"),
]
