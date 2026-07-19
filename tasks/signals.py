import logging
import threading
from django.db.models.signals import pre_save, post_save, post_delete
from django.core.cache import cache
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Task, Comment, ActivityLog, SearchDocument
from .embedding_service import embed_text
from notifications.services import notify
from notifications.models import Notification

logger = logging.getLogger('taskflow_api')

_thread_locals = threading.local()


def set_current_request(request):
    _thread_locals.request = request


def get_current_user():
    request = getattr(_thread_locals, 'request', None)
    if request is None:
        return None
    user = getattr(request, 'user', None)
    if user is not None and getattr(user, 'is_authenticated', False):
        return user
    return None


def index_for_search(content_type, object_id, project_id, text):
    try:
        embedding = embed_text(text)
    except Exception:
        logger.warning(f"Failed to embed {content_type}:{object_id} — search index skipped.", exc_info=True)
        embedding = None

    SearchDocument.objects.update_or_create(
        content_type=content_type, object_id=object_id,
        defaults={'project_id': project_id, 'text': text, 'embedding': embedding}
    )


@receiver(pre_save, sender=Task)
def capture_old_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_status = Task.objects.get(pk=instance.pk).status
        except Task.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


def broadcast_activity(activity_log):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            f'project_{activity_log.task.project_id}',
            {
                'type': 'activity_message',
                'data': {
                    'action': activity_log.action,
                    'detail': activity_log.detail,
                    'actor': activity_log.actor.username if activity_log.actor else None,
                    'task_title': activity_log.task.title,
                    'created_at': activity_log.created_at.isoformat(),
                }
            }
        )
    except Exception:
        logger.warning(f"Failed to broadcast activity for task {activity_log.task_id} — continuing anyway.", exc_info=True)


@receiver(post_save, sender=Task)
def log_task_save(sender, instance, created, **kwargs):
    actor = get_current_user()
    if created:
        log = ActivityLog.objects.create(task=instance, actor=actor, action=ActivityLog.ActionType.CREATED,
                                          detail=f"Task '{instance.title}' created")
        if instance.assigned_to:
            notify(
                recipient=instance.assigned_to, actor=actor,
                notification_type=Notification.NotificationType.TASK_ASSIGNED,
                message=f"You were assigned to '{instance.title}'",
                task=instance, project=instance.project,
            )
    else:
        old_status = getattr(instance, '_old_status', None)
        if old_status and old_status != instance.status:
            log = ActivityLog.objects.create(task=instance, actor=actor, action=ActivityLog.ActionType.STATUS_CHANGED,
                                              detail=f"Status changed from {old_status} to {instance.status}")
            if instance.assigned_to:
                notify(
                    recipient=instance.assigned_to, actor=actor,
                    notification_type=Notification.NotificationType.STATUS_CHANGED,
                    message=f"'{instance.title}' status changed to {instance.status}",
                    task=instance, project=instance.project,
                )
        else:
            log = ActivityLog.objects.create(task=instance, actor=actor, action=ActivityLog.ActionType.UPDATED,
                                              detail=f"Task '{instance.title}' updated")
    broadcast_activity(log)
    index_for_search('task', instance.id, instance.project_id, f"{instance.title}\n{instance.description}")


@receiver(post_save, sender=Comment)
def log_comment(sender, instance, created, **kwargs):
    if created:
        log = ActivityLog.objects.create(task=instance.task, actor=instance.author,
                                          action=ActivityLog.ActionType.COMMENTED,
                                          detail=f"{instance.author.username} commented")
        broadcast_activity(log)
        if instance.task.assigned_to:
            notify(
                recipient=instance.task.assigned_to, actor=instance.author,
                notification_type=Notification.NotificationType.COMMENT_ADDED,
                message=f"{instance.author.username} commented on '{instance.task.title}'",
                task=instance.task, project=instance.task.project,
            )
        index_for_search('comment', instance.id, instance.task.project_id, instance.body)


@receiver(post_save, sender=Task)
def invalidate_project_stats_cache_on_save(sender, instance, **kwargs):
    cache.delete(f'project_stats:{instance.project_id}')


@receiver(post_delete, sender=Task)
def invalidate_project_stats_cache_on_delete(sender, instance, **kwargs):
    cache.delete(f'project_stats:{instance.project_id}')