from django.contrib import admin

from .models import LibraryItem, PlaySession, Rating, SessionPlayer

admin.site.register([LibraryItem, Rating, PlaySession, SessionPlayer])
