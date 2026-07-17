import threading
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from .models import Task, Comment, ActivityLog
from django.core.cache import cache

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


@receiver(pre_save, sender=Task)
def capture_old_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_status = Task.objects.get(pk=instance.pk).status
        except Task.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Task)
def log_task_save(sender, instance, created, **kwargs):
    actor = get_current_user()
    if created:
        ActivityLog.objects.create(task=instance, actor=actor, action=ActivityLog.ActionType.CREATED,
                                    detail=f"Task '{instance.title}' created")
    else:
        old_status = getattr(instance, '_old_status', None)
        if old_status and old_status != instance.status:
            ActivityLog.objects.create(task=instance, actor=actor, action=ActivityLog.ActionType.STATUS_CHANGED,
                                        detail=f"Status changed from {old_status} to {instance.status}")
        else:
            ActivityLog.objects.create(task=instance, actor=actor, action=ActivityLog.ActionType.UPDATED,
                                        detail=f"Task '{instance.title}' updated")


@receiver(post_save, sender=Comment)
def log_comment(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(task=instance.task, actor=instance.author,
                                    action=ActivityLog.ActionType.COMMENTED,
                                    detail=f"{instance.author.username} commented")
        

@receiver(post_save, sender=Task)
def invalidate_project_stats_cache_on_save(sender, instance, **kwargs):
    cache.delete(f'project_stats:{instance.project_id}')


@receiver(post_delete, sender=Task)
def invalidate_project_stats_cache_on_delete(sender, instance, **kwargs):
    cache.delete(f'project_stats:{instance.project_id}')