import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock

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
    

@pytest.mark.django_db
def test_search_tasks_by_title(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    client.post('/api/tasks/', {'project': project_id, 'title': 'Fix login bug'})
    client.post('/api/tasks/', {'project': project_id, 'title': 'Update documentation'})

    response = client.get('/api/tasks/?search=login')
    assert response.status_code == 200
    assert response.data['count'] == 1
    assert 'login' in response.data['results'][0]['title'].lower()


@pytest.mark.django_db
def test_order_tasks_by_priority(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    client.post('/api/tasks/', {'project': project_id, 'title': 'Low priority task', 'priority': 'low'})
    client.post('/api/tasks/', {'project': project_id, 'title': 'High priority task', 'priority': 'high'})

    response = client.get('/api/tasks/?ordering=priority')
    assert response.status_code == 200
    assert response.data['count'] == 2
    

@pytest.mark.django_db
def test_upload_attachment(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    task_resp = client.post('/api/tasks/', {'project': project_id, 'title': 'Task 1'})
    task_id = task_resp.data['id']

    test_file = SimpleUploadedFile('report.txt', b'file contents here', content_type='text/plain')
    response = client.post(f'/api/tasks/{task_id}/attachments/', {'file': test_file}, format='multipart')
    assert response.status_code == 201
    assert response.data['original_filename'] == 'report.txt'


@pytest.mark.django_db
def test_export_csv(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    client.post('/api/tasks/', {'project': project_id, 'title': 'Task 1'})

    response = client.get('/api/tasks/export-csv/')
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv'
    content = response.content.decode('utf-8')
    assert 'Task 1' in content
    

@pytest.mark.django_db
@patch('tasks.views.generate_task_description')
def test_ai_generate_description(mock_generate, auth_client):
    mock_generate.return_value = "Set up the database schema and verify migrations run cleanly."
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']

    response = client.post('/api/tasks/ai-generate-description/', {
        'title': 'Set up database', 'project': project_id
    })
    assert response.status_code == 200
    assert 'description' in response.data
    mock_generate.assert_called_once()


@pytest.mark.django_db
@patch('tasks.views.suggest_priority')
def test_ai_suggest_priority(mock_suggest, auth_client):
    mock_suggest.return_value = ('high', 'This blocks all other development work.')
    client, user = auth_client

    response = client.post('/api/tasks/ai-suggest-priority/', {
        'title': 'Fix critical production outage'
    })
    assert response.status_code == 200
    assert response.data['priority'] == 'high'
    

@pytest.mark.django_db
def test_create_subtask(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    parent_resp = client.post('/api/tasks/', {'project': project_id, 'title': 'Parent task'})
    parent_id = parent_resp.data['id']

    response = client.post(f'/api/tasks/{parent_id}/subtasks/', {'title': 'Subtask 1'})
    assert response.status_code == 201
    assert response.data['parent_task'] == parent_id


@pytest.mark.django_db
def test_subtask_completion_percentage(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    parent_resp = client.post('/api/tasks/', {'project': project_id, 'title': 'Parent task'})
    parent_id = parent_resp.data['id']

    client.post(f'/api/tasks/{parent_id}/subtasks/', {'title': 'Sub 1', 'status': 'done'})
    client.post(f'/api/tasks/{parent_id}/subtasks/', {'title': 'Sub 2', 'status': 'todo'})

    response = client.get(f'/api/tasks/{parent_id}/')
    assert response.data['subtask_completion']['total'] == 2
    assert response.data['subtask_completion']['done'] == 1
    assert response.data['subtask_completion']['percentage'] == 50


@pytest.mark.django_db
def test_task_dependency_blocks(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    task_a = client.post('/api/tasks/', {'project': project_id, 'title': 'Task A'}).data
    task_b = client.post('/api/tasks/', {'project': project_id, 'title': 'Task B'}).data

    response = client.post(f'/api/tasks/{task_b["id"]}/block-by/{task_a["id"]}/')
    assert response.status_code == 200
    assert response.data['is_blocked'] is True


@pytest.mark.django_db
def test_task_dependency_prevents_circular(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    task_a = client.post('/api/tasks/', {'project': project_id, 'title': 'Task A'}).data
    task_b = client.post('/api/tasks/', {'project': project_id, 'title': 'Task B'}).data

    client.post(f'/api/tasks/{task_b["id"]}/block-by/{task_a["id"]}/')
    response = client.post(f'/api/tasks/{task_a["id"]}/block-by/{task_b["id"]}/')
    assert response.status_code == 400
    assert 'circular' in response.data['detail'].lower()
    

@pytest.mark.django_db
def test_start_and_stop_timer(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    task_resp = client.post('/api/tasks/', {'project': project_id, 'title': 'Task 1'})
    task_id = task_resp.data['id']

    start_resp = client.post(f'/api/tasks/{task_id}/time/start/')
    assert start_resp.status_code == 201
    assert start_resp.data['ended_at'] is None

    stop_resp = client.post(f'/api/tasks/{task_id}/time/stop/', {'note': 'Finished the setup'})
    assert stop_resp.status_code == 200
    assert stop_resp.data['ended_at'] is not None
    assert stop_resp.data['note'] == 'Finished the setup'


@pytest.mark.django_db
def test_cannot_start_second_timer_while_one_running(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    task_resp = client.post('/api/tasks/', {'project': project_id, 'title': 'Task 1'})
    task_id = task_resp.data['id']

    client.post(f'/api/tasks/{task_id}/time/start/')
    response = client.post(f'/api/tasks/{task_id}/time/start/')
    assert response.status_code == 400


@pytest.mark.django_db
def test_total_time_logged(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    task_resp = client.post('/api/tasks/', {'project': project_id, 'title': 'Task 1'})
    task_id = task_resp.data['id']

    client.post(f'/api/tasks/{task_id}/time/start/')
    client.post(f'/api/tasks/{task_id}/time/stop/')

    response = client.get(f'/api/tasks/{task_id}/')
    assert response.data['total_time_logged_minutes'] is not None
    

@pytest.mark.django_db
@patch('tasks.signals.embed_text')
def test_task_creation_indexes_search_document(mock_embed, auth_client):
    mock_embed.return_value = [0.1, 0.2, 0.3]
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    client.post('/api/tasks/', {'project': project_id, 'title': 'Fix the login bug', 'description': 'Users cannot log in'})

    from tasks.models import SearchDocument
    doc = SearchDocument.objects.filter(content_type='task').first()
    assert doc is not None
    assert 'login' in doc.text.lower()
    assert doc.embedding == [0.1, 0.2, 0.3]
    

@pytest.mark.django_db
def test_task_rejects_negative_estimated_hours(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']

    response = client.post('/api/tasks/', {
        'project': project_id, 'title': 'Task 1', 'estimated_hours': -5
    })
    assert response.status_code == 400