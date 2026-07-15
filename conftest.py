import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_user(db):
    def make_user(username="testuser", password="testpass123", **kwargs):
        return User.objects.create_user(username=username, password=password, **kwargs)
    return make_user


@pytest.fixture
def auth_client(api_client, create_user):
    user = create_user()
    response = api_client.post('/api/auth/login/', {'username': 'testuser', 'password': 'testpass123'})
    token = response.data['access']
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return api_client, user
