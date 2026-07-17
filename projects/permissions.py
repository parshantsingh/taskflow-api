from rest_framework import permissions
from .models import ProjectMembership


class IsProjectMember(permissions.BasePermission):
    """Allows access only to users who are a member (any role) of the project."""

    def has_object_permission(self, request, view, obj):
        return ProjectMembership.objects.filter(project=obj, user=request.user).exists()


class IsProjectAdminOrOwner(permissions.BasePermission):
    """Allows write access only to project owners/admins; read access to any member."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return ProjectMembership.objects.filter(project=obj, user=request.user).exists()
        return ProjectMembership.objects.filter(
            project=obj, user=request.user, role__in=['owner', 'admin']
        ).exists()
