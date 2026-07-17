from rest_framework import serializers
from .models import Task, Comment, ActivityLog
from projects.models import ProjectMembership


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'project', 'title', 'description', 'status', 'priority',
                  'assigned_to', 'due_date', 'created_at', 'updated_at']

    def validate_project(self, project):
        request = self.context['request']
        if not ProjectMembership.objects.filter(project=project, user=request.user).exists():
            raise serializers.ValidationError("You are not a member of this project.")
        return project


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Comment
        fields = ['id', 'task', 'author', 'body', 'created_at']
        read_only_fields = ['task']


class ActivityLogSerializer(serializers.ModelSerializer):
    actor = serializers.ReadOnlyField(source='actor.username')

    class Meta:
        model = ActivityLog
        fields = ['id', 'action', 'detail', 'actor', 'created_at']