# tracker/throttling.py
import logging
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.exceptions import Throttled
from django.conf import settings

logger = logging.getLogger(__name__)

class BurstRateThrottle(SimpleRateThrottle):
    scope = 'burst'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = f"user-{request.user.pk}"
        else:
            ident = self.get_ident(request)

        key = self.cache_format % {'scope': self.scope, 'ident': ident}
        logger.debug("BurstRateThrottle.get_cache_key scope=%s ident=%s key=%s", self.scope, ident, key)
        return key

    def throttle_failure(self):
        # include scope name in the message and use DRF's wait() to get seconds
        wait_seconds = int(self.wait() or 0)
        msg = f"Request was throttled by '{self.scope}' throttle. Try again in {wait_seconds} second(s)."
        logger.warning("BurstRateThrottle throttled: scope=%s wait=%s", self.scope, wait_seconds)
        raise Throttled(detail=msg, wait=wait_seconds)


class SustainedRateThrottle(SimpleRateThrottle):
    scope = 'sustained'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = f"user-{request.user.pk}"
        else:
            ident = self.get_ident(request)

        key = self.cache_format % {'scope': self.scope, 'ident': ident}
        logger.debug("SustainedRateThrottle.get_cache_key scope=%s ident=%s key=%s", self.scope, ident, key)
        return key

    def throttle_failure(self):
        wait_seconds = int(self.wait() or 0)
        msg = f"Request was throttled by '{self.scope}' throttle. Try again in {wait_seconds} second(s)."
        logger.warning("SustainedRateThrottle throttled: scope=%s wait=%s", self.scope, wait_seconds)
        raise Throttled(detail=msg, wait=wait_seconds)


class APIKeyRateThrottle(SimpleRateThrottle):
    scope = 'api_key'

    def get_cache_key(self, request, view):
        key = request.headers.get('X-API-KEY') or request.META.get('HTTP_X_API_KEY')
        valid_keys = getattr(settings, 'API_KEYS', [])
        if key and key in valid_keys:
            ident = f"apikey-{key}"
            cache_key = self.cache_format % {'scope': self.scope, 'ident': ident}
            logger.debug("APIKeyRateThrottle.get_cache_key scope=%s ident=%s key=%s", self.scope, ident, cache_key)
            return cache_key
        # not an API-key request -> don't apply this throttle
        logger.debug("APIKeyRateThrottle skipped (no valid API key)")
        return None

    def throttle_failure(self):
        wait_seconds = int(self.wait() or 0)
        msg = f"Request was throttled by '{self.scope}' throttle. Try again in {wait_seconds} second(s)."
        logger.warning("APIKeyRateThrottle throttled: scope=%s wait=%s", self.scope, wait_seconds)
        raise Throttled(detail=msg, wait=wait_seconds)
