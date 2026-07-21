from django.contrib import admin
from .models import Webhook, WebhookDelivery


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ['url', 'project', 'is_active', 'created_at']
    list_filter = ['is_active']


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ['webhook', 'event_type', 'success', 'response_status', 'created_at']
    list_filter = ['success', 'event_type']