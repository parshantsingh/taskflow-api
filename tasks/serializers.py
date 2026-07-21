from rest_framework import serializers
from .models import Task, Comment, ActivityLog, Attachment, TimeEntry
from projects.models import ProjectMembership


class TaskSerializer(serializers.ModelSerializer):
    subtask_completion = serializers.ReadOnlyField()
    is_blocked = serializers.SerializerMethodField()
    total_time_logged_minutes = serializers.ReadOnlyField()

    class Meta:
        model = Task
        fields = ['id', 'project', 'title', 'description', 'status', 'priority', 'estimated_hours',
                  'assigned_to', 'due_date', 'parent_task', 'blocked_by',
                  'subtask_completion', 'is_blocked', 'total_time_logged_minutes', 'created_at', 'updated_at']

    def get_is_blocked(self, obj):
        return obj.is_blocked()

    def validate_project(self, project):
        request = self.context['request']
        if not ProjectMembership.objects.filter(project=project, user=request.user).exists():
            raise serializers.ValidationError("You are not a member of this project.")
        return project
    
    def validate_estimated_hours(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Estimated hours must be greater than zero.")
        return value

    def validate(self, data):
        parent_task = data.get('parent_task') or getattr(self.instance, 'parent_task', None)
        if parent_task and self.instance and parent_task_id_conflicts_with_self(self.instance, parent_task):
            raise serializers.ValidationError("A task cannot be its own subtask.")
        return data


def parent_task_id_conflicts_with_self(instance, parent_task):
    if instance.pk == parent_task.pk:
        return True
    current = parent_task
    visited = set()
    while current is not None:
        if current.pk in visited:
            break
        visited.add(current.pk)
        if current.pk == instance.pk:
            return True
        current = current.parent_task
    return False

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
        

class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.ReadOnlyField(source='uploaded_by.username')

    class Meta:
        model = Attachment
        fields = ['id', 'task', 'file', 'uploaded_by', 'original_filename', 'file_size', 'uploaded_at']
        read_only_fields = ['task', 'original_filename', 'file_size']
        

class TimeEntrySerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    duration_minutes = serializers.ReadOnlyField()

    class Meta:
        model = TimeEntry
        fields = ['id', 'task', 'username', 'started_at', 'ended_at', 'duration_minutes', 'note']
        read_only_fields = ['task', 'started_at']