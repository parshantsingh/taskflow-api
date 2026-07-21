from rest_framework import serializers
from .models import Webhook, WebhookDelivery
from projects.models import ProjectMembership


class WebhookSerializer(serializers.ModelSerializer):
    secret = serializers.CharField(read_only=True)

    class Meta:
        model = Webhook
        fields = ['id', 'project', 'url', 'secret', 'event_types', 'is_active', 'created_at']
        read_only_fields = ['secret', 'created_at']

    def validate_event_types(self, value):
        valid = {choice[0] for choice in Webhook.EVENT_CHOICES}
        invalid = set(value) - valid
        if invalid:
            raise serializers.ValidationError(f"Invalid event types: {', '.join(invalid)}")
        return value

    def validate_project(self, project):
        request = self.context['request']
        membership = ProjectMembership.objects.filter(project=project, user=request.user).first()
        if not membership:
            raise serializers.ValidationError("You are not a member of this project.")
        if membership.role not in ['owner', 'admin']:
            raise serializers.ValidationError("Only project owners/admins can manage webhooks.")
        return project
    
    def validate_url(self, value):
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("Webhook URL must use http or https.")
        blocked_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '169.254.169.254']
        if any(host in value for host in blocked_hosts):
            raise serializers.ValidationError("Webhook URL cannot target internal/local addresses.")
        return value

class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = ['id', 'event_type', 'response_status', 'success', 'attempt_number', 'error_message', 'created_at']
