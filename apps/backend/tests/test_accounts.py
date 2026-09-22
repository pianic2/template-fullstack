import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_current_user_requires_auth_and_returns_email_identity():
    user = User.objects.create_user(email="ada@example.com", password="correct-horse-battery")
    client = APIClient()
    assert client.get("/api/v1/users/me").status_code == 401
    client.force_authenticate(user=user)
    response = client.get("/api/v1/users/me")
    assert response.status_code == 200
    assert response.json()["email"] == "ada@example.com"


@pytest.mark.django_db
def test_mobile_jwt_can_access_current_user():
    user = User.objects.create_user(email="mobile@example.com", password="correct-horse-battery")
    client = APIClient()
    token = client.post(
        "/api/v1/auth/token", {"email": user.email, "password": "correct-horse-battery"}
    )
    assert token.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.json()['access']}")
    assert client.get("/api/v1/users/me").json()["email"] == user.email


@pytest.mark.django_db
def test_browser_session_login_requires_csrf_and_uses_session_cookie():
    User.objects.create_user(email="web@example.com", password="correct-horse-battery")
    client = APIClient(enforce_csrf_checks=True)
    csrf_response = client.get("/api/v1/auth/csrf")
    csrf = csrf_response.json()["csrfToken"]
    response = client.post(
        "/api/v1/auth/session/login",
        {"email": "web@example.com", "password": "correct-horse-battery"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert response.status_code == 200
    assert "sessionid" in response.cookies
    assert client.get("/api/v1/users/me").status_code == 200
