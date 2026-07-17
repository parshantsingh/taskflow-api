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


@pytest.mark.django_db
def test_password_reset_request_existing_email(create_user, api_client):
    create_user(email='testuser@example.com')
    response = api_client.post('/api/auth/password-reset/', {'email': 'testuser@example.com'})
    assert response.status_code == 200


@pytest.mark.django_db
def test_password_reset_request_nonexistent_email_returns_same_response(api_client):
    response = api_client.post('/api/auth/password-reset/', {'email': 'nobody@example.com'})
    assert response.status_code == 200
    assert 'sent' in response.data['detail'].lower()


@pytest.mark.django_db
def test_password_reset_confirm_invalid_token(create_user, api_client):
    user = create_user()
    response = api_client.post('/api/auth/password-reset-confirm/', {
        'uid': 'invaliduid', 'token': 'invalidtoken', 'new_password': 'newstrongpass123'
    })
    assert response.status_code == 400


@pytest.mark.django_db
def test_login_locks_after_too_many_failed_attempts(create_user, api_client):
    create_user()
    for _ in range(5):
        api_client.post('/api/auth/login/', {'username': 'testuser', 'password': 'wrongpass'})

    response = api_client.post('/api/auth/login/', {'username': 'testuser', 'password': 'wrongpass'})
    assert response.status_code == 429