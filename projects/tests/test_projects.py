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
    

@pytest.mark.django_db
def test_project_member_count_annotation(auth_client, create_user):
    client, user = auth_client
    create_user(username='teammate2')
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    assert project_resp.data['member_count'] == 1

    client.post(f'/api/projects/{project_id}/members/', {'username': 'teammate2'})
    response = client.get(f'/api/projects/{project_id}/')
    assert response.data['member_count'] == 2


@pytest.mark.django_db
def test_project_stats_endpoint(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    client.post('/api/tasks/', {'project': project_id, 'title': 'Task 1', 'status': 'todo'})
    client.post('/api/tasks/', {'project': project_id, 'title': 'Task 2', 'status': 'done'})

    response = client.get(f'/api/projects/{project_id}/stats/')
    assert response.status_code == 200
    assert response.data['total_tasks'] == 2
    assert response.data['by_status']['todo'] == 1
    assert response.data['by_status']['done'] == 1


@pytest.mark.django_db
def test_project_stats_cache_invalidated_on_new_task(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']

    first = client.get(f'/api/projects/{project_id}/stats/')
    assert first.data['total_tasks'] == 0

    client.post('/api/tasks/', {'project': project_id, 'title': 'New task'})

    second = client.get(f'/api/projects/{project_id}/stats/')
    assert second.data['total_tasks'] == 1


@pytest.mark.django_db
def test_project_list_has_no_n_plus_one_queries(auth_client, django_assert_max_num_queries):
    client, user = auth_client
    for i in range(5):
        client.post('/api/projects/', {'name': f'Project {i}'})

    with django_assert_max_num_queries(10):
        client.get('/api/projects/')