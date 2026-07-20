from .models import Webhook
from .tasks import deliver_webhook


def trigger_webhook_event(project, event_type, data):
    webhooks = Webhook.objects.filter(project=project, is_active=True)
    for webhook in webhooks:
        if event_type in webhook.event_types:
            deliver_webhook.delay(webhook.id, event_type, data)
