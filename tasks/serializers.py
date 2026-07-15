from rest_framework import serializers
from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'project', 'title', 'description', 'status', 'priority',
                  'assigned_to', 'due_date', 'created_at', 'updated_at']

    def validate_project(self, project):
        request = self.context['request']
        if project.owner != request.user:
            raise serializers.ValidationError("You do not own this project.")
        return project
