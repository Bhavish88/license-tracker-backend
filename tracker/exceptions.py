# tracker/exceptions.py
from rest_framework.views import exception_handler
from rest_framework.exceptions import Throttled

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None and isinstance(exc, Throttled):
        # DRF already sets 'Retry-After' header when Throttled has wait,
        # but add a numeric field to the JSON body for easier parsing in Postman/frontend
        wait = getattr(exc, 'wait', None)
        try:
            wait_seconds = int(wait or 0)
        except Exception:
            wait_seconds = 0
        # Add or replace a helpful field in the response body
        response.data['expected_available_in'] = wait_seconds

    return response
