"""Authenticated, CSRF-protected Weeple Chat API; every conversation lookup checks membership."""

from django.db.models import Count, F, OuterRef, Q, Subquery, Sum
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from community import chat_services as service
from community.chat_serializers import (
    ContactQuerySerializer,
    ConversationQuerySerializer,
    MessageInputSerializer,
    MessageQuerySerializer,
    PreferencesSerializer,
    ReadInputSerializer,
    RecipientSerializer,
)
from community.models import DirectConversation, DirectMessage, UserBlock
from profiles.models import Profile


class ChatReadThrottle(UserRateThrottle):
    scope = "chat-read"
    rate = "120/min"


class ChatWriteThrottle(UserRateThrottle):
    scope = "chat-write"
    rate = "30/min"


class ChatAPIView(APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (ChatReadThrottle,)

    def dispatch(self, request, *args, **kwargs):
        with service.request_cache():
            return super().dispatch(request, *args, **kwargs)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not service.active(request.user):
            raise PermissionDenied("Your account is no longer active.")


def validated(serializer_class, data):
    value = serializer_class(data=data)
    value.is_valid(raise_exception=True)
    return value.validated_data


class ChatPreferencesView(ChatAPIView):
    def get(self, request):
        return Response(PreferencesSerializer(service.preferences(request.user)).data)

    def patch(self, request):
        value = PreferencesSerializer(data=request.data, partial=True)
        value.is_valid(raise_exception=True)
        result = service.set_preferences(request.user, value.validated_data)
        return Response(PreferencesSerializer(result).data)


class ChatBlockListView(ChatAPIView):
    def get(self, request):
        blocks = (
            UserBlock.objects.filter(blocker=request.user).select_related("blocked__profile").order_by("-created_at")
        )
        return Response([service.player_summary(item.blocked) for item in blocks])

    def post(self, request):
        values = validated(RecipientSerializer, request.data)
        service.set_block(request.user, values["user_id"])
        return Response({"detail": "Player blocked. You can still view existing conversation history."}, status=201)


class ChatBlockDetailView(ChatAPIView):
    def delete(self, request, user_id):
        service.remove_block(request.user, user_id)
        return Response(status=204)


class ChatContactsView(ChatAPIView):
    def get(self, request):
        values = validated(ContactQuerySerializer, request.query_params)
        query = values["search"].strip()
        profiles = Profile.objects.filter(user__is_active=True, user__deleted_at__isnull=True).exclude(
            user=request.user
        )
        if len(query) >= 2:
            profiles = profiles.filter(Q(privacy_level=Profile.PUBLIC) | Q(friends__user=request.user))
            profiles = profiles.filter(display_name__icontains=query)
        else:
            profiles = profiles.filter(friends__user=request.user)
        hidden = UserBlock.objects.filter(blocker=request.user).values("blocked_id")
        hidden_by = UserBlock.objects.filter(blocked=request.user).values("blocker_id")
        profiles = profiles.exclude(user_id__in=hidden).exclude(user_id__in=hidden_by).select_related("user")
        items = list(profiles.distinct().order_by("display_name", "pk")[:51])
        return Response(
            {
                "results": [
                    dict(service.player_summary(p.user), can_send=service.can_send(request.user, p.user))
                    for p in items[:50]
                ],
                "has_more": len(items) > 50,
            }
        )


class ChatConversationListView(ChatAPIView):
    def get(self, request):
        offset = validated(ConversationQuerySerializer, request.query_params)["offset"]
        conversations = (
            DirectConversation.objects.filter(Q(user_a=request.user) | Q(user_b=request.user))
            .select_related(
                "user_a__profile", "user_b__profile", "user_a__chat_preferences", "user_b__chat_preferences"
            )
            .order_by("-updated_at", "-pk")
        )
        latest = DirectMessage.objects.filter(conversation_id=OuterRef("pk")).order_by("-pk").values("pk")[:1]
        conversations = conversations.annotate(latest_id=Subquery(latest))
        items = list(conversations[offset : offset + 31])
        messages = DirectMessage.objects.in_bulk([item.latest_id for item in items if item.latest_id])
        for item in items:
            item._latest_message = messages.get(item.latest_id)
        return Response(
            {
                "results": [service.conversation_summary(c, request.user) for c in items[:30]],
                "has_more": len(items) > 30,
            }
        )

    def post(self, request):
        values = validated(RecipientSerializer, request.data)
        conversation = service.open_conversation(request.user, values["user_id"])
        return Response(service.conversation_summary(conversation, request.user), status=201)


class ChatConversationDetailView(ChatAPIView):
    def get(self, request, conversation_id):
        return Response(
            service.conversation_summary(service.conversation_for(request.user, conversation_id), request.user)
        )


class ChatMessagesView(ChatAPIView):
    def get_throttles(self):
        if self.request.method == "POST":
            return [ChatWriteThrottle()]
        return super().get_throttles()

    def get(self, request, conversation_id):
        conversation = service.conversation_for(request.user, conversation_id)
        values = validated(MessageQuerySerializer, request.query_params)
        messages = conversation.messages.all()
        if "after" in values:
            items = list(messages.filter(pk__gt=values["after"]).order_by("pk")[:51])
            results = items[:50]
        else:
            if "before" in values:
                messages = messages.filter(pk__lt=values["before"])
            items = list(messages.order_by("-pk")[:51])
            results = list(reversed(items[:50]))
        return Response(
            {
                "results": [service.message_summary(m, request.user, conversation) for m in results],
                "has_more": len(items) > 50,
            }
        )

    def post(self, request, conversation_id):
        values = validated(MessageInputSerializer, request.data)
        message, created = service.send_message(request.user, conversation_id, values["body"], values["client_id"])
        conversation = service.conversation_for(request.user, conversation_id)
        return Response(service.message_summary(message, request.user, conversation), status=201 if created else 200)


class ChatReadView(ChatAPIView):
    def post(self, request, conversation_id):
        values = validated(ReadInputSerializer, request.data)
        service.mark_read(request.user, conversation_id, values["message_id"])
        return Response({"detail": "Conversation read position updated."})


class ChatPresenceView(ChatAPIView):
    def post(self, request):
        service.heartbeat(request.user)
        return Response(status=204)


class ChatSummaryView(ChatAPIView):
    def get(self, request):
        user = request.user
        hidden = UserBlock.objects.filter(blocker=user).values("blocked_id")
        hidden_by = UserBlock.objects.filter(blocked=user).values("blocker_id")
        conversations = DirectConversation.objects.filter(Q(user_a=user) | Q(user_b=user)).exclude(
            Q(user_a_id__in=hidden) | Q(user_b_id__in=hidden) | Q(user_a_id__in=hidden_by) | Q(user_b_id__in=hidden_by)
        )
        unread = (Q(user_a=user, messages__pk__gt=F("read_a")) | Q(user_b=user, messages__pk__gt=F("read_b"))) & ~Q(
            messages__sender=user
        )
        count = (
            conversations.annotate(unread=Count("messages", filter=unread)).aggregate(total=Sum("unread"))["total"] or 0
        )
        return Response(
            {
                "user_id": str(user.pk),
                "unread_count": count,
                "message_notifications": service.preferences(user).message_notifications,
            }
        )
