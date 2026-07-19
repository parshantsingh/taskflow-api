from django.conf import settings
from django.db import models
from projects.models import Project


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = 'todo', 'To Do'
        IN_PROGRESS = 'in_progress', 'In Progress'
        DONE = 'done', 'Done'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    parent_task = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subtasks')
    blocked_by = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='blocks')
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    
    @property
    def subtask_completion(self):
        subtasks = self.subtasks.all()
        if not subtasks.exists():
            return None
        total = subtasks.count()
        done = subtasks.filter(status='done').count()
        return {'total': total, 'done': done, 'percentage': round((done / total) * 100)}

    def is_blocked(self):
        return self.blocked_by.exclude(status='done').exists()

    @property
    def total_time_logged_minutes(self):
        completed_entries = self.time_entries.filter(ended_at__isnull=False)
        total = sum((e.duration_minutes for e in completed_entries), 0)
        return total
    

class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_comments')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.task.title}"


class ActivityLog(models.Model):
    class ActionType(models.TextChoices):
        CREATED = 'created', 'Created'
        UPDATED = 'updated', 'Updated'
        STATUS_CHANGED = 'status_changed', 'Status Changed'
        COMMENTED = 'commented', 'Commented'
        ASSIGNED = 'assigned', 'Assigned'
        DELETED = 'deleted', 'Deleted'

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='activity_logs')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='task_activities')
    action = models.CharField(max_length=20, choices=ActionType.choices)
    detail = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} on {self.task.title} by {self.actor}"
    
    
def attachment_upload_path(instance, filename):
    return f'task_attachments/{instance.task.project_id}/{instance.task_id}/{filename}'


class Attachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=attachment_upload_path)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='uploaded_attachments')
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.original_filename
    

class TimeEntry(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='time_entries')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='time_entries')
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-started_at']

    @property
    def duration_minutes(self):
        if not self.ended_at:
            return None
        delta = self.ended_at - self.started_at
        return round(delta.total_seconds() / 60)

    def __str__(self):
        return f"{self.user.username} on {self.task.title}"
    
    
class SearchDocument(models.Model):
    """
    A flattened, embeddable representation of a piece of project content
    (a task or a comment). Kept separate from Task/Comment so we can index
    other content types later without touching those models.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='search_documents')
    content_type = models.CharField(max_length=20)  # 'task' or 'comment'
    object_id = models.PositiveIntegerField()
    text = models.TextField()
    embedding = models.JSONField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['content_type', 'object_id']

    def __str__(self):
        return f"{self.content_type}:{self.object_id}"