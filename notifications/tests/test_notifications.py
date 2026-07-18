import pytest


@pytest.mark.django_db
def test_notification_created_on_task_assignment(auth_client, create_user):
    client, user = auth_client
    teammate = create_user(username='teammate')
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    client.post(f'/api/projects/{project_id}/members/', {'username': 'teammate'})

    client.post('/api/tasks/', {'project': project_id, 'title': 'Task 1', 'assigned_to': teammate.id})

    from notifications.models import Notification
    assert Notification.objects.filter(recipient=teammate, notification_type='task_assigned').exists()


@pytest.mark.django_db
def test_notification_created_on_project_invite(auth_client, create_user):
    client, user = auth_client
    teammate = create_user(username='teammate')
    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']

    client.post(f'/api/projects/{project_id}/members/', {'username': 'teammate'})

    from notifications.models import Notification
    assert Notification.objects.filter(recipient=teammate, notification_type='project_invite').exists()


@pytest.mark.django_db
def test_mark_notification_as_read(auth_client, create_user):
    client, user = auth_client
    teammate_client_user = create_user(username='teammate', password='testpass123')

    from rest_framework.test import APIClient
    teammate_client = APIClient()
    login_resp = teammate_client.post('/api/auth/login/', {'username': 'teammate', 'password': 'testpass123'})
    teammate_client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_resp.data["access"]}')

    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    client.post(f'/api/projects/{project_id}/members/', {'username': 'teammate'})

    list_resp = teammate_client.get('/api/notifications/')
    assert list_resp.data['count'] == 1
    notification_id = list_resp.data['results'][0]['id']

    mark_resp = teammate_client.post(f'/api/notifications/{notification_id}/mark-read/')
    assert mark_resp.status_code == 200
    assert mark_resp.data['is_read'] is True


@pytest.mark.django_db
def test_unread_count(auth_client, create_user):
    client, user = auth_client
    teammate_user = create_user(username='teammate', password='testpass123')

    from rest_framework.test import APIClient
    teammate_client = APIClient()
    login_resp = teammate_client.post('/api/auth/login/', {'username': 'teammate', 'password': 'testpass123'})
    teammate_client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_resp.data["access"]}')

    project_resp = client.post('/api/projects/', {'name': 'Project A'})
    project_id = project_resp.data['id']
    client.post(f'/api/projects/{project_id}/members/', {'username': 'teammate'})

    response = teammate_client.get('/api/notifications/unread-count/')
    assert response.status_code == 200
    assert response.data['unread_count'] == 1
