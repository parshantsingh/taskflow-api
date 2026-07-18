import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from projects.models import ProjectMembership


class ProjectActivityConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.group_name = f'project_{self.project_id}'
        user = self.scope.get('user')

        if not user or not user.is_authenticated:
            await self.close()
            return

        is_member = await self.is_project_member(user, self.project_id)
        if not is_member:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def activity_message(self, event):
        await self.send(text_data=json.dumps(event['data']))

    @database_sync_to_async
    def is_project_member(self, user, project_id):
        return ProjectMembership.objects.filter(project_id=project_id, user=user).exists()
