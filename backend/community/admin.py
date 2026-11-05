from django.contrib import admin

from community.models import EventRSVP, FriendRequest, GameEvent

admin.site.register([FriendRequest, GameEvent, EventRSVP])
