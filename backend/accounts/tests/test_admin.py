"""
Admin smoke tests.

Django's admin is configured declaratively, so mistakes in fieldsets or forms
surface only when a page is rendered -- not at import time and not by the system
check framework. A misconfigured `add_form` produced a 500 on the add-user page
that unit tests would never have caught, hence these.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.fixture
def staff_client(client, db):
    User.objects.create_superuser(email="staff@example.com", password="LocalDevOnly!2026")
    client.login(username="staff@example.com", password="LocalDevOnly!2026")
    return client


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name",
    [
        "admin:index",
        "admin:accounts_user_changelist",
        "admin:accounts_user_add",
        "admin:accounts_corporateaccount_changelist",
        "admin:accounts_corporateaccount_add",
    ],
)
def test_admin_pages_render(staff_client, url_name):
    response = staff_client.get(reverse(url_name))
    assert response.status_code == 200


@pytest.mark.django_db
def test_user_change_page_renders(staff_client):
    user = User.objects.create_user(email="customer@example.com", first_name="Zoë")
    response = staff_client.get(reverse("admin:accounts_user_change", args=[user.pk]))
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_can_create_user_without_usable_password(staff_client):
    """
    Staff must be able to create an account with no usable password -- the state
    every imported legacy customer starts in, pending a reset.
    """
    response = staff_client.post(
        reverse("admin:accounts_user_add"),
        {"email": "nopass@example.com", "usable_password": "false"},
        follow=True,
    )
    assert response.status_code == 200
    created = User.objects.get(email="nopass@example.com")
    assert not created.has_usable_password()


@pytest.mark.django_db
def test_anonymous_is_redirected_from_admin(client):
    response = client.get(reverse("admin:accounts_user_changelist"))
    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]


@pytest.mark.django_db
def test_non_staff_cannot_reach_admin(client):
    User.objects.create_user(email="customer2@example.com", password="LocalDevOnly!2026")
    client.login(username="customer2@example.com", password="LocalDevOnly!2026")
    response = client.get(reverse("admin:accounts_user_changelist"))
    assert response.status_code == 302
