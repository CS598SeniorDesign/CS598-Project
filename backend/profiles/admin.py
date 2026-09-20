from django.contrib import admin

from .models import GameGroup, PlayerTag, Profile

admin.site.register([Profile, GameGroup, PlayerTag])
