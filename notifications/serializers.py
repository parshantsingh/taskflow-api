from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    actor_username = serializers.ReadOnlyField(source='actor.username')
    task_title = serializers.ReadOnlyField(source='task.title')
    project_name = serializers.ReadOnlyField(source='project.name')

    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'message', 'actor_username', 'task', 'task_title',
                  'project', 'project_name', 'is_read', 'created_at']
