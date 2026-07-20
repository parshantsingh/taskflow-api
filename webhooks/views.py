from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Webhook, WebhookDelivery
from .serializers import WebhookSerializer, WebhookDeliverySerializer


class WebhookViewSet(viewsets.ModelViewSet):
    serializer_class = WebhookSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Webhook.objects.none()
        return Webhook.objects.filter(project__memberships__user=self.request.user).distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'], url_path='deliveries')
    def deliveries(self, request, pk=None):
        webhook = self.get_object()
        deliveries = webhook.deliveries.all()[:50]
        return Response(WebhookDeliverySerializer(deliveries, many=True).data)
