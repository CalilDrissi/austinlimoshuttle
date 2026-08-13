"""
Account URLs.

Uses Django's built-in password reset views rather than hand-rolled ones. They
already handle the parts that are easy to get subtly wrong: signed one-time
tokens, expiry, invalidation once the password changes, and a response that does
not reveal whether an address is registered.

Only the templates are ours.
"""

from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import MigrationPasswordResetForm

app_name = "accounts"

urlpatterns = [
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            form_class=MigrationPasswordResetForm,
            template_name="accounts/password_reset_form.html",
            email_template_name="accounts/email/password_reset.txt",
            html_email_template_name="accounts/email/password_reset.html",
            subject_template_name="accounts/email/password_reset_subject.txt",
            success_url="/accounts/password-reset/sent/",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/sent/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url="/accounts/reset/done/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
    path(
        "password-change/",
        auth_views.PasswordChangeView.as_view(
            template_name="accounts/password_change_form.html",
            success_url="/accounts/password-change/done/",
        ),
        name="password_change",
    ),
    path(
        "password-change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="accounts/password_change_done.html",
        ),
        name="password_change_done",
    ),
]
