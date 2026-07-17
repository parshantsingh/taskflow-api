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


@pytest.mark.django_db
def test_invite_member(auth_client, create_user):
    client, user = auth_client
    other_user = create_user(username='teammate')
    project_resp = client.post('/api/projects/', {'name': 'Team Project'})
    project_id = project_resp.data['id']

    response = client.post(f'/api/projects/{project_id}/members/', {'username': 'teammate', 'role': 'member'})
    assert response.status_code == 201
    assert response.data['username'] == 'teammate'


@pytest.mark.django_db
def test_cannot_remove_owner(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Solo Project'})
    project_id = project_resp.data['id']

    response = client.get(f'/api/projects/{project_id}/members/')
    owner_membership_id = response.data[0]['user']

    remove_response = client.delete(f'/api/projects/{project_id}/members/{owner_membership_id}/')
    assert remove_response.status_code == 400