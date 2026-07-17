from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Project, ProjectMembership

User = get_user_model()


class ProjectMembershipSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = ProjectMembership
        fields = ['id', 'user', 'username', 'role', 'joined_at']
        read_only_fields = ['joined_at']


class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    member_count = serializers.IntegerField(source='annotated_member_count', read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'owner', 'member_count', 'created_at', 'updated_at']


class AddMemberSerializer(serializers.Serializer):
    username = serializers.CharField()
    role = serializers.ChoiceField(choices=ProjectMembership.Role.choices, default=ProjectMembership.Role.MEMBER)

    def validate_username(self, value):
        try:
            User.objects.get(username=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with this username.")
        return value