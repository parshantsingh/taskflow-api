import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger('taskflow_api')


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            'error': True,
            'detail': response.data.get('detail', response.data) if isinstance(response.data, dict) else response.data,
            'status_code': response.status_code,
        }
        return response

    # DRF didn't recognize this exception — it's an unhandled server error.
    # Log it with full context instead of letting Django's default 500 page leak through.
    view = context.get('view')
    logger.error(
        f"Unhandled exception in {view.__class__.__name__ if view else 'unknown view'}: {exc}",
        exc_info=True
    )
    return Response(
        {'error': True, 'detail': 'An unexpected error occurred.', 'status_code': 500},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
