"""Session-authenticated account actions scoped strictly to request.user."""

from django.contrib.auth import get_user_model, logout
from django.db import OperationalError, transaction
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.serializers import AccountPasswordSerializer, DeleteAccountSerializer
from users.services import (
    ImportInProgress,
    check_hosted_events,
    clear_game_data,
    schedule_cover_cleanup,
)
from users.throttles import AccountActionThrottle


def locked_user(request):
    """Reload authentication under the same database lock used by BGG import workers."""
    try:
        user = (
            get_user_model()
            .objects.select_for_update(nowait=True)
            .filter(pk=request.user.pk, is_active=True, deleted_at__isnull=True)
            .first()
        )
    except OperationalError as error:
        cause = error.__cause__
        if getattr(cause, "sqlstate", None) == "55P03" or getattr(cause, "pgcode", None) == "55P03":
            raise ImportInProgress() from error
        raise
    if user is None:
        raise NotAuthenticated("Your account is no longer available. Please sign in again.")
    request.user = user
    return user


class ClearGameDataView(APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (AccountActionThrottle,)

    def post(self, request):
        """Clear only this account's tracking data after password validation."""
        with transaction.atomic():
            user = locked_user(request)
            serializer = AccountPasswordSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            clear_game_data(user)
        return Response({"detail": "Your game data was cleared and your BGG account was unlinked."})


class DeleteAccountView(APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (AccountActionThrottle,)

    def post(self, request):
        """Delete this account atomically; reject community-data cascades before any changes."""
        with transaction.atomic():
            user = locked_user(request)
            serializer = DeleteAccountSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            check_hosted_events(user)
            clear_game_data(user)
            schedule_cover_cleanup(user)
            user.delete()
        # Deleted users also fail authentication in every other existing Django session.
        logout(request)
        return Response({"detail": "Your QuestLog account has been deleted."})
