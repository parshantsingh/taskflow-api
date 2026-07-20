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


@pytest.fixture(autouse=True)
def clear_cache():
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()
    

@pytest.fixture
def celery_eager():
    from taskflow_api.celery import app as celery_app
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = False
    celery_app.conf.task_eager_propagates = False