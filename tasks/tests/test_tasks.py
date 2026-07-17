import pytest


@pytest.mark.django_db
def test_create_task(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']

    response = client.post('/api/tasks/', {
        'project': project_id, 'title': 'Write tests', 'status': 'todo', 'priority': 'high'
    })
    assert response.status_code == 201
    assert response.data['title'] == 'Write tests'


@pytest.mark.django_db
def test_task_filter_by_status(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    client.post('/api/tasks/', {'project': project_id, 'title': 'Task 1', 'status': 'done'})
    client.post('/api/tasks/', {'project': project_id, 'title': 'Task 2', 'status': 'todo'})

    response = client.get('/api/tasks/?status=done')
    assert response.data['count'] == 1


@pytest.mark.django_db
def test_add_comment(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    task_resp = client.post('/api/tasks/', {'project': project_id, 'title': 'Task 1'})
    task_id = task_resp.data['id']

    response = client.post(f'/api/tasks/{task_id}/comments/', {'body': 'Looks good!'})
    assert response.status_code == 201
    assert response.data['author'] == user.username


@pytest.mark.django_db
def test_activity_log_created_on_task_creation(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    task_resp = client.post('/api/tasks/', {'project': project_id, 'title': 'Task 1'})
    task_id = task_resp.data['id']

    response = client.get(f'/api/tasks/{task_id}/activity/')
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]['action'] == 'created'