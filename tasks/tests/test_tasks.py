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
