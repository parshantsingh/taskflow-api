import csv
from django.http import HttpResponse
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from .models import Task, Attachment
from .serializers import TaskSerializer, CommentSerializer, ActivityLogSerializer, AttachmentSerializer
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