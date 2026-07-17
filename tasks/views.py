from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import Task
from .serializers import TaskSerializer, CommentSerializer, ActivityLogSerializer
from .filters import TaskFilter
from .tasks import send_due_date_reminder


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = TaskFilter
    ordering_fields = ['created_at', 'due_date', 'priority', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Task.objects.none()
        return Task.objects.filter(project__memberships__user=self.request.user).distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        task = serializer.save()
        if task.due_date:
            send_due_date_reminder.apply_async(args=[task.id], eta=task.due_date)

    @action(detail=True, methods=['get', 'post'], url_path='comments')
    def comments(self, request, pk=None):
        task = self.get_object()

        if request.method == 'GET':
            comments = task.comments.all()
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)

        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(task=task, author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='activity')
    def activity(self, request, pk=None):
        task = self.get_object()
        logs = task.activity_logs.all()
        serializer = ActivityLogSerializer(logs, many=True)
        return Response(serializer.data)