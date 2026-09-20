import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import Client

LOGIN = "/_allauth/browser/v1/auth/login"

@pytest.fixture
def user(db):
    test_user = get_user_model().objects.create_user(email="a@example.com", password="S3cure-pass!x")
    EmailAddress.objects.create(user=test_user, email=test_user.email, verified=True, primary=True)
    return test_user

def test_login_sets_httponly_lax_cookie(user):
    response = Client().post(LOGIN, {"email": "a@example.com", "password": "S3cure-pass!x"},
                        content_type="application/json")
    assert response.status_code == 200
    cookies = response.cookies["sessionid"]
    assert cookies["httponly"] and cookies["samesite"] == "Lax"

def test_post_without_csrf_rejected(user):
    response = Client(enforce_csrf_checks=True).post(
        LOGIN, {"email": "a@example.com", "password": "S3cure-pass!x"},
        content_type="application/json")
    assert response.status_code == 403