from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission


def is_feature_enabled(flag_name: str) -> bool:
    """
    Returns whether a feature flag is switched on for the current environment.

    :param flag_name: The flag's key in settings.FEATURE_FLAGS (e.g. "ANALYTICS").
    :type flag_name: str
    :returns: True if the flag is declared and enabled, otherwise False.
    :rtype: bool
    """

    return bool(settings.FEATURE_FLAGS.get(flag_name, False))


class FeatureFlagPermission(BasePermission):
    """Hides a view behind the feature flag named by the view's feature_flag attribute.

    A disabled feature responds with 404 rather than 403 so that clients cannot tell the endpoint exists. List this
    class before IsAuthenticated so anonymous requests to a disabled feature also receive 404.

    Example:
        class AnalyticsSummaryView(APIView):
            feature_flag = "ANALYTICS"
            permission_classes = [FeatureFlagPermission, IsAuthenticated]
    """

    def has_permission(self, request, view) -> bool:
        flag_name: str | None = getattr(view, "feature_flag", None)

        if not flag_name:
            raise ImproperlyConfigured(f"{type(view).__name__} uses FeatureFlagPermission but sets no feature_flag.")

        if not is_feature_enabled(flag_name):
            raise NotFound()

        return True
