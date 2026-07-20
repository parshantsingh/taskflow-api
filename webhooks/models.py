import secrets
from django.conf import settings
from django.db import models
from projects.models import Project


class Webhook(models.Model):
    EVENT_CHOICES = [
        ('task.created', 'Task Created'),
        ('task.updated', 'Task Updated'),
        ('task.status_changed', 'Task Status Changed'),
        ('comment.created', 'Comment Created'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='webhooks')
    url = models.URLField()
    secret = models.CharField(max_length=64, default=secrets.token_hex, editable=False)
    event_types = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='webhooks_created')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.url} ({self.project.name})"


class WebhookDelivery(models.Model):
    webhook = models.ForeignKey(Webhook, on_delete=models.CASCADE, related_name='deliveries')
    event_type = models.CharField(max_length=50)
    payload = models.JSONField()
    response_status = models.IntegerField(null=True, blank=True)
    success = models.BooleanField(default=False)
    attempt_number = models.PositiveIntegerField(default=1)
    error_message = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.webhook_id} - {self.event_type} - {'OK' if self.success else 'FAIL'}"