from rest_framework import serializers
from .models import Task
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