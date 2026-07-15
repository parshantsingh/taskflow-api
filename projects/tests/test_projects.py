import pytest


@pytest.mark.django_db
def test_create_project(auth_client):
    client, user = auth_client
    response = client.post('/api/projects/', {'name': 'My Project', 'description': 'Test'})
    assert response.status_code == 201
    assert response.data['owner'] == user.username


@pytest.mark.django_db
def test_list_projects_only_own(auth_client):
    client, user = auth_client
    client.post('/api/projects/', {'name': 'Project A'})
    response = client.get('/api/projects/')
    assert response.status_code == 200
    assert response.data['count'] == 1
