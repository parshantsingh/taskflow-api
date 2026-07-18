from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache


def health_check(request):
    health = {'status': 'ok', 'checks': {}}
    overall_ok = True

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health['checks']['database'] = 'ok'
    except Exception as e:
        health['checks']['database'] = f'error: {str(e)}'
        overall_ok = False

    try:
        cache.set('health_check_key', 'ok', timeout=5)
        cache.get('health_check_key')
        health['checks']['cache'] = 'ok'
    except Exception as e:
        health['checks']['cache'] = f'error: {str(e)}'
        overall_ok = False

    health['status'] = 'ok' if overall_ok else 'degraded'
    return JsonResponse(health, status=200 if overall_ok else 503)
