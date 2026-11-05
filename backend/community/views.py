"""
API endpoints for QuestLog's community features: friend requests, game groups, game nights (events), the activity
feed, trending games, and the community summary used for notifications.

Every endpoint requires authentication. Groups, events and players a user may not see answer 404, the same as ones
that do not exist.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, cast

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from community.models import EventRSVP, GameEvent
from community.serializers import (
    ActivitySerializer,
    CommunitySummarySerializer,
    EventListQuerySerializer,
    EventRSVPSerializer,
    FeedQuerySerializer,
    FriendRequestCreateSerializer,
    FriendRequestSerializer,
    GameEventDetailSerializer,
    GameEventSerializer,
    GameEventWriteSerializer,
    GameGroupDetailSerializer,
    GameGroupSerializer,
    GameGroupWriteSerializer,
    GroupMemberSerializer,
    RSVPInputSerializer,
    TrendingGameSerializer,
    TrendingQuerySerializer,
)
from community.services import (
    CommunitySummaryService,
    EventService,
    FeedService,
    FriendshipService,
    GroupService,
    TrendingService,
)
from core.throttles import FriendRequestRateThrottle
from profiles.models import GameGroup
from users.models import User


@contextmanager
def service_errors_as_api_errors() -> Generator[None, None, None]:
    """
    Report a Django ValidationError raised by a community service as a 400 response. (DRF already turns Django's
    PermissionDenied and Http404 into 403 and 404.)

    :raises rest_framework.exceptions.ValidationError: When the service rejected the request.
    """
    try:
        yield
    except DjangoValidationError as error:
        if hasattr(error, "message_dict"):
            raise ValidationError(error.message_dict) from error
        raise ValidationError({"detail": error.messages[0]}) from error


def requesting_user(request: Any) -> User:
    """
    :returns: The authenticated user (every view here requires authentication).
    """
    return cast("User", request.user)


class FriendRequestListView(APIView):
    """
    The requesting user's pending friend requests, and sending new ones.

    get:
        ``incoming`` (sent to the user) and ``outgoing`` (sent by the user) pending requests, newest first.
    post:
        Ask a player to be friends (``user_id``). Returns 201 with the new request; 200 with the existing request if
        one is already pending; or 200 with ``status`` ACCEPTED if that player had already asked the user, who are now
        friends. 400 for yourself or an existing friend; 404 for a player the user cannot find in the player search
        (including Private profiles). Limited to 30 requests per hour.
    """

    permission_classes = [IsAuthenticated]

    def get_throttles(self):
        if self.request.method == "POST":
            return [*super().get_throttles(), FriendRequestRateThrottle()]
        return super().get_throttles()

    def get(self, request):
        incoming, outgoing = FriendshipService.pending_requests(requesting_user(request))
        return Response(
            {
                "incoming": FriendRequestSerializer(incoming, many=True).data,
                "outgoing": FriendRequestSerializer(outgoing, many=True).data,
            }
        )

    def post(self, request):
        serializer = FriendRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with service_errors_as_api_errors():
            friend_request, outcome = FriendshipService.send_request(
                requesting_user(request), serializer.validated_data["user_id"]
            )
        response_status = status.HTTP_201_CREATED if outcome == FriendshipService.CREATED else status.HTTP_200_OK
        return Response(FriendRequestSerializer(friend_request).data, status=response_status)


class FriendRequestDetailView(APIView):
    """
    delete:
        Withdraw a pending request the user sent. 404 if there is no such pending request from the user.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, request_id: int):
        FriendshipService.cancel(requesting_user(request), request_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FriendRequestAcceptView(APIView):
    """
    post:
        Accept a pending request sent to the user; the two become friends. 404 if there is no such pending request.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, request_id: int):
        friend_request = FriendshipService.accept(requesting_user(request), request_id)
        return Response(FriendRequestSerializer(friend_request).data)


class FriendRequestDeclineView(APIView):
    """
    post:
        Decline a pending request sent to the user. 404 if there is no such pending request.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, request_id: int):
        friend_request = FriendshipService.decline(requesting_user(request), request_id)
        return Response(FriendRequestSerializer(friend_request).data)


class FriendDetailView(APIView):
    """
    delete:
        End a friendship, for both users. 404 if the two are not friends.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id):
        FriendshipService.remove_friend(requesting_user(request), user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class GameGroupViewSet(viewsets.ViewSet):
    """
    The requesting user's game groups. Groups are visible only to their members; only the owner (creator) can change
    them.

    list:
        The user's groups, alphabetically, with ``member_count`` and ``is_owner``.
    create:
        Create a group (``name``, optional ``description``), optionally adding some of the user's friends
        (``member_ids``). The user becomes its owner. 400 if a member is not the user's friend.
    retrieve:
        A group with its ``members``.
    partial_update:
        Rename or re-describe a group (owner only; 403 for other members).
    destroy:
        Delete a group, with its events and the play sessions logged for it (owner only).
    members:
        Add one of the owner's friends (``user_id``). Owner only.
    remove_member:
        Remove a member. Owner only; the owner cannot remove themselves.
    leave:
        Leave a group. The owner cannot leave; they delete the group instead.
    """

    permission_classes = [IsAuthenticated]
    lookup_value_regex = r"\d+"

    def list(self, request):
        groups = GroupService.groups_for(requesting_user(request))
        return Response(GameGroupSerializer(groups, many=True, context={"request": request}).data)

    def create(self, request):
        serializer = GameGroupWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with service_errors_as_api_errors():
            group = GroupService.create(requesting_user(request), **serializer.validated_data)
        return Response(self._detail(group), status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        group = GroupService.group_for_member(requesting_user(request), int(pk))
        return Response(self._detail(group))

    def partial_update(self, request, pk=None):
        user = requesting_user(request)
        group = GroupService.group_for_member(user, int(pk))
        serializer = GameGroupWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changes = {field: value for field, value in serializer.validated_data.items() if field != "member_ids"}
        GroupService.update(user, group, changes)
        return Response(self._detail(GroupService.group_for_member(user, group.pk)))

    def destroy(self, request, pk=None):
        user = requesting_user(request)
        GroupService.delete(user, GroupService.group_for_member(user, int(pk)))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def members(self, request, pk=None):
        user = requesting_user(request)
        group = GroupService.group_for_member(user, int(pk))
        serializer = GroupMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with service_errors_as_api_errors():
            GroupService.add_member(user, group, serializer.validated_data["user_id"])
        return Response(self._detail(GroupService.group_for_member(user, group.pk)))

    @action(detail=True, methods=["delete"], url_path=r"members/(?P<user_id>[0-9a-f-]{36})", url_name="remove-member")
    def remove_member(self, request, pk=None, user_id=None):
        user = requesting_user(request)
        group = GroupService.group_for_member(user, int(pk))
        try:
            member_id = uuid.UUID(str(user_id))
        except ValueError:
            raise NotFound("No player with this ID.") from None
        with service_errors_as_api_errors():
            GroupService.remove_member(user, group, member_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        user = requesting_user(request)
        group = GroupService.group_for_member(user, int(pk))
        with service_errors_as_api_errors():
            GroupService.leave(user, group)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _detail(self, group: GameGroup) -> dict[str, Any]:
        context = {"request": self.request, "members": GroupService.members_of(group)}
        return GameGroupDetailSerializer(group, context=context).data


class GameEventViewSet(viewsets.ViewSet):
    """
    Game nights the requesting user can see: events in their groups, and events (without a group) hosted by them or
    their friends.

    list:
        Upcoming events, soonest first. ``?scope=past`` lists past events, most recent first. ``?days=N`` limits
        upcoming events to the next N days; ``?group_id=`` to one group. Each has ``going_count`` and the user's own
        ``my_rsvp``.
    create:
        Plan an event: ``title``, ``starts_at`` (in the future), and optionally ``description``, ``location``,
        ``game_id`` (BGG ID in the catalog) and ``group_id`` (one of the user's groups). The user is its host and is
        recorded as going.
    retrieve:
        An event with everyone's ``rsvps``.
    partial_update:
        Change an event (host only).
    destroy:
        Cancel an event (host only).
    rsvp:
        Answer an event (``status``: GOING, MAYBE or NOT_GOING). Answering again replaces the earlier answer.
    """

    permission_classes = [IsAuthenticated]
    lookup_value_regex = r"\d+"

    def list(self, request):
        user = requesting_user(request)
        query = EventListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        events = list(EventService.list_for(user, **query.validated_data))
        my_rsvps = dict(EventRSVP.objects.filter(user=user, event__in=events).values_list("event_id", "status"))
        context = {"request": request, "my_rsvps": my_rsvps}
        return Response(GameEventSerializer(events, many=True, context=context).data)

    def create(self, request):
        serializer = GameEventWriteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        with service_errors_as_api_errors():
            event = EventService.create(requesting_user(request), serializer.validated_data)
        return Response(self._detail(event), status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        return Response(self._detail(EventService.event_for(requesting_user(request), int(pk))))

    def partial_update(self, request, pk=None):
        user = requesting_user(request)
        event = EventService.event_for(user, int(pk))
        serializer = GameEventWriteSerializer(data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        with service_errors_as_api_errors():
            event = EventService.update(user, event, serializer.validated_data)
        return Response(self._detail(event))

    def destroy(self, request, pk=None):
        user = requesting_user(request)
        EventService.delete(user, EventService.event_for(user, int(pk)))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def rsvp(self, request, pk=None):
        user = requesting_user(request)
        event = EventService.event_for(user, int(pk))
        serializer = RSVPInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with service_errors_as_api_errors():
            rsvp = EventService.rsvp(user, event, serializer.validated_data["status"])
        return Response(EventRSVPSerializer(rsvp).data)

    def _detail(self, event: GameEvent) -> dict[str, Any]:
        context = {"request": self.request, "rsvps": EventService.rsvps_for(event)}
        return GameEventDetailSerializer(event, context=context).data


class CommunityFeedView(APIView):
    """
    get:
        Recent activity by the user and their friends: plays logged and games added to libraries or wishlists, newest
        first. ``?limit=`` (1-50, default 20). Friends with a Private profile are left out.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = FeedQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        activities = FeedService.recent_activity(requesting_user(request), query.validated_data["limit"])
        return Response(ActivitySerializer(activities, many=True, context={"request": request}).data)


class TrendingGamesView(APIView):
    """
    get:
        The games played most on QuestLog in the last ``?days=`` days (default 7), topped up with BGG's highest-ranked
        games when fewer were played. ``?limit=`` (1-20, default 4). Built from everyone's plays in aggregate.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = TrendingQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        games = TrendingService.trending(**query.validated_data)
        return Response(
            {
                "days": query.validated_data["days"],
                "results": TrendingGameSerializer(games, many=True, context={"request": request}).data,
            }
        )


class CommunitySummaryView(APIView):
    """
    get:
        Counts for notifications: ``pending_friend_requests``, ``upcoming_events`` (in the next 7 days, not declined),
        and ``next_event``.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        summary = CommunitySummaryService.summary(requesting_user(request))
        return Response(CommunitySummarySerializer(summary).data)
