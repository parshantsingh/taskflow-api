import pytest


@pytest.mark.django_db
def test_register_user(api_client):
    response = api_client.post('/api/auth/register/', {
        'username': 'newuser', 'email': 'new@example.com', 'password': 'strongpass123'
    })
    assert response.status_code == 201


@pytest.mark.django_db
def test_login_success(create_user, api_client):
    create_user()
    response = api_client.post('/api/auth/login/', {'username': 'testuser', 'password': 'testpass123'})
    assert response.status_code == 200
    assert 'access' in response.data


@pytest.mark.django_db
def test_login_wrong_password(create_user, api_client):
    create_user()
    response = api_client.post('/api/auth/login/', {'username': 'testuser', 'password': 'wrongpass'})
    assert response.status_code == 401
