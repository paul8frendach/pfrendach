"""FindThe90 Shop URL patterns."""

from django.urls import path

from . import views

app_name = "shop"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("printful/webhook/", views.printful_webhook, name="printful_webhook"),
    path("<slug:slug>/", views.product_detail, name="product_detail"),
]
