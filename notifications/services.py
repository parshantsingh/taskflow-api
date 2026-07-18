from .models import Notification


def notify(recipient, notification_type, message, actor=None, task=None, project=None):
    if recipient is None or (actor is not None and recipient == actor):
        return None
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        message=message,
        task=task,
        project=project,
    )
