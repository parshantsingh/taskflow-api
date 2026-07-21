import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_create_webhook(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']

    response = client.post('/api/webhooks/', {
        'project': project_id, 'url': 'https://example.com/hook', 'event_types': ['task.created']
    }, format='json')
    assert response.status_code == 201
    assert 'secret' in response.data


@pytest.mark.django_db
def test_non_admin_cannot_create_webhook(auth_client, create_user):
    client, user = auth_client
    create_user(username='teammate', password='testpass123')
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    client.post(f'/api/projects/{project_id}/members/', {'username': 'teammate', 'role': 'member'})

    teammate_client = APIClient()
    login = teammate_client.post('/api/auth/login/', {'username': 'teammate', 'password': 'testpass123'})
    teammate_client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    response = teammate_client.post('/api/webhooks/', {
        'project': project_id, 'url': 'https://example.com/hook', 'event_types': ['task.created']
    }, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
@patch('webhooks.tasks.requests.post')
def test_webhook_delivered_on_task_creation(mock_post, auth_client, celery_eager):
    mock_post.return_value = MagicMock(status_code=200)

    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    client.post('/api/webhooks/', {
        'project': project_id, 'url': 'https://example.com/hook', 'event_types': ['task.created']
    }, format='json')

    client.post('/api/tasks/', {'project': project_id, 'title': 'Task 1'})

    from webhooks.models import WebhookDelivery
    assert WebhookDelivery.objects.filter(event_type='task.created', success=True).exists()

    _, kwargs = mock_post.call_args
    assert 'X-TaskFlow-Signature' in kwargs['headers']


@pytest.mark.django_db
@patch('webhooks.tasks.requests.post')
def test_webhook_not_triggered_for_unsubscribed_event(mock_post, auth_client, celery_eager):
    mock_post.return_value = MagicMock(status_code=200)

    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    client.post('/api/webhooks/', {
        'project': project_id, 'url': 'https://example.com/hook', 'event_types': ['comment.created']
    }, format='json')

    client.post('/api/tasks/', {'project': project_id, 'title': 'Task 1'})

    assert not mock_post.called


@pytest.mark.django_db
def test_webhook_rejects_non_http_url(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']

    response = client.post('/api/webhooks/', {
        'project': project_id, 'url': 'ftp://example.com/hook', 'event_types': ['task.created']
    }, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_webhook_rejects_localhost_url(auth_client):
    client, user = auth_client
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']

    response = client.post('/api/webhooks/', {
        'project': project_id, 'url': 'http://localhost:8000/hook', 'event_types': ['task.created']
    }, format='json')
    assert response.status_code == 400