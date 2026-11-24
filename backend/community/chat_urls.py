"""Included under the existing /api/v1/ prefix."""

from django.urls import path

from community.chat_views import (
    ChatBlockDetailView,
    ChatBlockListView,
    ChatContactsView,
    ChatConversationDetailView,
    ChatConversationListView,
    ChatMessagesView,
    ChatPreferencesView,
    ChatPresenceView,
    ChatReadView,
    ChatSummaryView,
)

urlpatterns = [
    path("chat/preferences/", ChatPreferencesView.as_view(), name="chat-preferences"),
    path("chat/blocks/", ChatBlockListView.as_view(), name="chat-blocks"),
    path("chat/blocks/<uuid:user_id>/", ChatBlockDetailView.as_view(), name="chat-block-detail"),
    path("chat/contacts/", ChatContactsView.as_view(), name="chat-contacts"),
    path("chat/conversations/", ChatConversationListView.as_view(), name="chat-conversations"),
    path("chat/conversations/<int:conversation_id>/", ChatConversationDetailView.as_view(), name="chat-conversation"),
    path("chat/conversations/<int:conversation_id>/messages/", ChatMessagesView.as_view(), name="chat-messages"),
    path("chat/conversations/<int:conversation_id>/read/", ChatReadView.as_view(), name="chat-read"),
    path("chat/presence/", ChatPresenceView.as_view(), name="chat-presence"),
    path("chat/summary/", ChatSummaryView.as_view(), name="chat-summary"),
]