from __future__ import annotations

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

LOCAL_MEMORY_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}


@pytest.fixture(autouse=True)
def isolated_bgg_settings(settings):
    """
    Give every catalog test its own empty in-memory cache and no spacing between BGG requests.

    The files in ``test_data`` are trimmed copies of real BGG XML API2 responses, so tests replay real structure
    without sending requests.
    """
    settings.CACHES = LOCAL_MEMORY_CACHE
    settings.BGG_MINIMUM_SECONDS_BETWEEN_REQUESTS = 0
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()
