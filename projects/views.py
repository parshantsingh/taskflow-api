from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Count, OuterRef, Exists
from django.core.cache import cache
from .models import Project, ProjectMembership
from .serializers import ProjectSerializer, ProjectMembershipSerializer, AddMemberSerializer
from .permissions import IsProjectAdminOrOwner
from tasks.ai_service import summarize_project
from django.utils import timezone
from datetime import timedelta
from tasks.models import Task

User = get_user_model()


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectAdminOrOwner]

    def get_queryset(self):
            if getattr(self, 'swagger_fake_view', False):
                return Project.objects.none()
            member_subquery = ProjectMembership.objects.filter(project=OuterRef('pk'), user=self.request.user)
            return Project.objects.filter(Exists(member_subquery)).select_related('owner').annotate(
                annotated_member_count=Count('memberships', distinct=True)
            )

    def perform_create(self, serializer):
        project = serializer.save(owner=self.request.user)
        ProjectMembership.objects.create(project=project, user=self.request.user, role=ProjectMembership.Role.OWNER)
        # Manually set the annotation on this instance since it wasn't fetched
        # through get_queryset()'s annotated query — DRF serializes this same
        # object right after this method returns.
        project.annotated_member_count = 1

    @action(detail=True, methods=['get', 'post'], url_path='members')
    def members(self, request, pk=None):
        project = self.get_object()

        if request.method == 'GET':
            memberships = project.memberships.select_related('user').all()
            serializer = ProjectMembershipSerializer(memberships, many=True)
            return Response(serializer.data)

        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get(username=serializer.validated_data['username'])
        membership, created = ProjectMembership.objects.get_or_create(
            project=project, user=user, defaults={'role': serializer.validated_data['role']}
        )
        if not created:
            return Response({'detail': 'User is already a member.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ProjectMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='members/(?P<user_id>[^/.]+)')
    def remove_member(self, request, pk=None, user_id=None):
        project = self.get_object()
        membership = ProjectMembership.objects.filter(project=project, user_id=user_id).first()
        if not membership:
            return Response({'detail': 'Membership not found.'}, status=status.HTTP_404_NOT_FOUND)
        if membership.role == ProjectMembership.Role.OWNER:
            return Response({'detail': 'Cannot remove the project owner.'}, status=status.HTTP_400_BAD_REQUEST)
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='stats')
    def stats(self, request, pk=None):
        project = self.get_object()
        cache_key = f'project_stats:{project.id}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        status_counts = project.tasks.values('status').annotate(count=Count('id'))
        priority_counts = project.tasks.values('priority').annotate(count=Count('id'))
        data = {
            'total_tasks': project.tasks.count(),
            'by_status': {item['status']: item['count'] for item in status_counts},
            'by_priority': {item['priority']: item['count'] for item in priority_counts},
        }
        cache.set(cache_key, data, timeout=60)
        return Response(data)
    
    @action(detail=True, methods=['get'], url_path='ai-summary')
    def ai_summary(self, request, pk=None):
        project = self.get_object()
        cache_key = f'project_ai_summary:{project.id}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response({'summary': cached, 'cached': True})

        tasks_data = list(project.tasks.values('title', 'status', 'priority'))
        if not tasks_data:
            return Response({'summary': 'No tasks yet in this project.', 'cached': False})

        try:
            summary = summarize_project(project.name, tasks_data)
        except Exception as e:
            return Response({'detail': f'AI service error: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)

        cache.set(cache_key, summary, timeout=300)
        return Response({'summary': summary, 'cached': False})
    

    @action(detail=False, methods=['get'], url_path='analytics/overview')
    def analytics_overview(self, request):
        cache_key = f'analytics_overview:{request.user.id}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        projects = Project.objects.filter(memberships__user=request.user).distinct()
        seven_days_ago = timezone.now() - timedelta(days=7)

        data = {
            'total_projects': projects.count(),
            'total_tasks': Task.objects.filter(project__in=projects).count(),
            'tasks_by_status': dict(
                Task.objects.filter(project__in=projects).values('status').annotate(count=Count('id')).values_list('status', 'count')
            ),
            'tasks_completed_last_7_days': Task.objects.filter(
                project__in=projects, status='done', updated_at__gte=seven_days_ago
            ).count(),
            'overdue_tasks': Task.objects.filter(
                project__in=projects, due_date__lt=timezone.now(), status__in=['todo', 'in_progress']
            ).count(),
        }
        cache.set(cache_key, data, timeout=120)
        return Response(data)