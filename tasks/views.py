import csv
from django.http import HttpResponse
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Task, Attachment, TimeEntry
from .serializers import TaskSerializer, CommentSerializer, ActivityLogSerializer, AttachmentSerializer, TimeEntrySerializer
from .filters import TaskFilter
from .tasks import send_due_date_reminder
from .ai_service import generate_task_description, suggest_priority


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
            return Task.objects.filter(
                project__memberships__user=self.request.user
            ).distinct().select_related('project', 'assigned_to')

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
    
    @action(detail=True, methods=['get', 'post'], url_path='attachments', parser_classes=[MultiPartParser, FormParser])
    def attachments(self, request, pk=None):
        task = self.get_object()

        if request.method == 'GET':
            attachments = task.attachments.select_related('uploaded_by').all()
            serializer = AttachmentSerializer(attachments, many=True)
            return Response(serializer.data)

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'detail': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        attachment = Attachment.objects.create(
            task=task,
            file=uploaded_file,
            uploaded_by=request.user,
            original_filename=uploaded_file.name,
            file_size=uploaded_file.size,
        )
        serializer = AttachmentSerializer(attachment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='attachments/(?P<attachment_id>[^/.]+)')
    def delete_attachment(self, request, pk=None, attachment_id=None):
        task = self.get_object()
        attachment = task.attachments.filter(id=attachment_id).first()
        if not attachment:
            return Response({'detail': 'Attachment not found.'}, status=status.HTTP_404_NOT_FOUND)
        attachment.file.delete(save=False)
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='export-csv')
    def export_csv(self, request):
        queryset = self.filter_queryset(self.get_queryset())

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="tasks_export.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Title', 'Project', 'Status', 'Priority', 'Assigned To', 'Due Date', 'Created At'])
        for task in queryset:
            writer.writerow([
                task.id, task.title, task.project.name, task.status, task.priority,
                task.assigned_to.username if task.assigned_to else '',
                task.due_date, task.created_at,
            ])
        return response
    
    @action(detail=True, methods=['post'], url_path='block-by/(?P<blocker_id>[^/.]+)')
    def add_blocker(self, request, pk=None, blocker_id=None):
        task = self.get_object()
        blocker = self.get_queryset().filter(id=blocker_id).first()
        if not blocker:
            return Response({'detail': 'Blocking task not found or not accessible.'}, status=status.HTTP_404_NOT_FOUND)
        if blocker.id == task.id:
            return Response({'detail': 'A task cannot block itself.'}, status=status.HTTP_400_BAD_REQUEST)
        if self._creates_cycle(task, blocker):
            return Response({'detail': 'This would create a circular dependency.'}, status=status.HTTP_400_BAD_REQUEST)

        task.blocked_by.add(blocker)
        return Response(TaskSerializer(task, context={'request': request}).data)

    @action(detail=True, methods=['delete'], url_path='block-by/(?P<blocker_id>[^/.]+)')
    def remove_blocker(self, request, pk=None, blocker_id=None):
        task = self.get_object()
        task.blocked_by.remove(blocker_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _creates_cycle(self, task, new_blocker):
        # Would adding new_blocker as a blocker of `task` create a cycle?
        # Walk new_blocker's own blockers — if we ever reach `task`, it's a cycle.
        visited = set()
        to_check = [new_blocker]
        while to_check:
            current = to_check.pop()
            if current.id == task.id:
                return True
            if current.id in visited:
                continue
            visited.add(current.id)
            to_check.extend(current.blocked_by.all())
        return False

    @action(detail=True, methods=['post'], url_path='subtasks')
    def create_subtask(self, request, pk=None):
        parent = self.get_object()
        data = request.data.copy()
        data['project'] = parent.project_id
        data['parent_task'] = parent.id
        serializer = TaskSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='duplicate')
    def duplicate(self, request, pk=None):
        original = self.get_object()
        copy = Task.objects.create(
            project=original.project,
            title=f"{original.title} (copy)",
            description=original.description,
            status=Task.Status.TODO,
            priority=original.priority,
            assigned_to=original.assigned_to,
            estimated_hours=original.estimated_hours,
        )
        return Response(TaskSerializer(copy, context={'request': request}).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='time/start')
    def start_timer(self, request, pk=None):
        task = self.get_object()
        if TimeEntry.objects.filter(task=task, user=request.user, ended_at__isnull=True).exists():
            return Response({'detail': 'A timer is already running for this task.'}, status=status.HTTP_400_BAD_REQUEST)

        entry = TimeEntry.objects.create(task=task, user=request.user, started_at=timezone.now())
        return Response(TimeEntrySerializer(entry).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='time/stop')
    def stop_timer(self, request, pk=None):
        task = self.get_object()
        entry = TimeEntry.objects.filter(task=task, user=request.user, ended_at__isnull=True).first()
        if not entry:
            return Response({'detail': 'No running timer found for this task.'}, status=status.HTTP_400_BAD_REQUEST)

        entry.ended_at = timezone.now()
        entry.note = request.data.get('note', '')
        entry.save(update_fields=['ended_at', 'note'])
        return Response(TimeEntrySerializer(entry).data)

    @action(detail=True, methods=['get'], url_path='time')
    def time_entries(self, request, pk=None):
        task = self.get_object()
        entries = task.time_entries.select_related('user').all()
        return Response(TimeEntrySerializer(entries, many=True).data)

    @action(detail=False, methods=['post'], url_path='ai-generate-description')
    def ai_generate_description(self, request):
        title = request.data.get('title')
        project_id = request.data.get('project')
        if not title or not project_id:
            return Response({'detail': 'title and project are required.'}, status=status.HTTP_400_BAD_REQUEST)

        project = Task.objects.filter(project_id=project_id).first()
        project_name = project.project.name if project else "this project"

        try:
            description = generate_task_description(title, project_name)
        except Exception as e:
            return Response({'detail': f'AI service error: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({'description': description})

    @action(detail=False, methods=['post'], url_path='ai-suggest-priority')
    def ai_suggest_priority(self, request):
        title = request.data.get('title')
        description = request.data.get('description', '')
        if not title:
            return Response({'detail': 'title is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            priority, reason = suggest_priority(title, description)
        except Exception as e:
            return Response({'detail': f'AI service error: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({'priority': priority, 'reason': reason})