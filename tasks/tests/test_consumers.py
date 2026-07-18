import pytest
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from taskflow_api.asgi import application
from django.contrib.auth import get_user_model
from projects.models import Project, ProjectMembership

User = get_user_model()


@database_sync_to_async
def create_user_and_project():
    user = User.objects.create_user(username='wsuser', password='testpass123')
    project = Project.objects.create(name='WS Project', owner=user)
    ProjectMembership.objects.create(project=project, user=user, role='owner')
    return user, project


@pytest.mark.django_db(transaction=True)
async def test_websocket_rejects_unauthenticated_connection():
    communicator = WebsocketCommunicator(application, "/ws/projects/1/activity/")
    connected, _ = await communicator.connect()
    assert connected is False
    await communicator.disconnect()
