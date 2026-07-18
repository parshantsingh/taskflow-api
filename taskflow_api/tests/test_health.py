import pytest
from django.test import Client


@pytest.mark.django_db
def test_health_check_returns_ok():
    client = Client()
    response = client.get('/health/')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['checks']['database'] == 'ok'
    assert data['checks']['cache'] == 'ok'
