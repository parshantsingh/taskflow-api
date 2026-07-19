import pytest
from unittest.mock import patch


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
        

@pytest.mark.django_db
@patch('projects.views.summarize_project')
def test_ai_project_summary(mock_summarize, auth_client):
    mock_summarize.return_value = "The project is progressing well with 2 tasks in progress."
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    client.post('/api/tasks/', {'project': project_id, 'title': 'Task 1'})

    response = client.get(f'/api/projects/{project_id}/ai-summary/')
    assert response.status_code == 200
    assert 'summary' in response.data
    
    
@pytest.mark.django_db
def test_analytics_overview(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    client.post('/api/tasks/', {'project': project_id, 'title': 'Task 1', 'status': 'done'})
    client.post('/api/tasks/', {'project': project_id, 'title': 'Task 2', 'status': 'todo'})

    response = client.get('/api/projects/analytics/overview/')
    assert response.status_code == 200
    assert response.data['total_projects'] == 1
    assert response.data['total_tasks'] == 2
    assert response.data['tasks_by_status']['done'] == 1
    assert response.data['tasks_by_status']['todo'] == 1
    

@pytest.mark.django_db
@patch('projects.views.answer_project_question')
@patch('projects.views.embed_query')
def test_ask_project_question(mock_embed_query, mock_answer, auth_client):
    mock_embed_query.return_value = [0.1, 0.2, 0.3]
    mock_answer.return_value = "The login bug is currently blocking the release."

    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']

    from tasks.models import SearchDocument
    SearchDocument.objects.create(
        project_id=project_id, content_type='task', object_id=1,
        text='Fix login bug blocking release', embedding=[0.1, 0.2, 0.31]
    )

    response = client.post(f'/api/projects/{project_id}/ask/', {'question': 'What is blocking the release?'})
    assert response.status_code == 200
    assert 'answer' in response.data
    assert response.data['sources_used'] >= 1


@pytest.mark.django_db
@patch('projects.views.embed_query')
def test_ask_returns_no_match_when_nothing_relevant(mock_embed_query, auth_client):
    mock_embed_query.return_value = [0.9, 0.9, 0.9]
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Empty Project'})
    project_id = project_resp.data['id']

    response = client.post(f'/api/projects/{project_id}/ask/', {'question': 'Anything at all?'})
    assert response.status_code == 200
    assert response.data['sources_used'] == 0