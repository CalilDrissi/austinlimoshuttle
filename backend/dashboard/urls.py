"""Dashboard URLs."""

from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("dispatch/", views.dispatch, name="dispatch"),
    path("bookings/", views.booking_list, name="bookings"),
    path("bookings/<str:reference>/", views.booking_detail, name="booking_detail"),
    path("bookings/<str:reference>/update/", views.booking_update, name="booking_update"),
    path("bookings/<str:reference>/refund/", views.issue_refund, name="issue_refund"),
    path("settings/payments/", views.payment_settings, name="payment_settings"),
    path("settings/paypal/", views.paypal_settings, name="paypal_settings"),
    path("settings/email/", views.email_settings, name="email_settings"),
    path("enquiries/", views.enquiry_inbox, name="enquiries"),
    path("enquiries/<int:pk>/", views.enquiry_detail, name="enquiry_detail"),
]
