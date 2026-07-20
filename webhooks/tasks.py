import hashlib
import hmac
import json
import requests
from celery import shared_task
from .models import Webhook, WebhookDelivery


@shared_task(bind=True, max_retries=3)
def deliver_webhook(self, webhook_id, event_type, data):
    try:
        webhook = Webhook.objects.get(id=webhook_id, is_active=True)
    except Webhook.DoesNotExist:
        return f"Webhook {webhook_id} not found or inactive."

    payload = {'event': event_type, 'data': data}
    body = json.dumps(payload, default=str).encode('utf-8')
    signature = hmac.new(webhook.secret.encode('utf-8'), body, hashlib.sha256).hexdigest()

    headers = {
        'Content-Type': 'application/json',
        'X-TaskFlow-Event': event_type,
        'X-TaskFlow-Signature': signature,
    }

    attempt_number = self.request.retries + 1

    try:
        response = requests.post(webhook.url, data=body, headers=headers, timeout=5)
    except requests.RequestException as exc:
        WebhookDelivery.objects.create(
            webhook=webhook, event_type=event_type, payload=payload,
            success=False, attempt_number=attempt_number, error_message=str(exc)[:500],
        )
        raise self.retry(countdown=2 ** attempt_number, exc=exc)

    success = 200 <= response.status_code < 300
    WebhookDelivery.objects.create(
        webhook=webhook, event_type=event_type, payload=payload,
        response_status=response.status_code, success=success, attempt_number=attempt_number,
    )

    if not success:
        raise self.retry(countdown=2 ** attempt_number, exc=Exception(f"Non-2xx response: {response.status_code}"))

    return f"Delivered {event_type} to webhook {webhook_id}"
