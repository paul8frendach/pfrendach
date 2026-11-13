from django.urls import path

from . import views

app_name = "create"

urlpatterns = [
    path("", views.index, name="index"),
    path("photography/", views.photography, name="photography"),
    path("request/", views.request_film, name="request"),
    path("request/thanks/", views.request_thanks, name="request_thanks"),
    path("book/", views.book, name="book"),
    path("book/success/", views.book_success, name="book_success"),
    path("book/cancel/", views.book_cancel, name="book_cancel"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
    # Client portal
    path("account/", views.account, name="account"),
    path("signin/", views.signin, name="signin"),
    path("signout/", views.signout, name="signout"),
    path("service/<slug:slug>/", views.service_detail, name="service_detail"),
    path("<slug:slug>/", views.work_detail, name="work_detail"),
]
