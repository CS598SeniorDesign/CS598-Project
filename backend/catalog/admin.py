# Register your models here.
from django.contrib import admin

from .models import Artist, BoardGame, Category, Designer, Family, Mechanic, Publisher

admin.site.register([BoardGame, Category, Mechanic, Publisher, Designer, Artist, Family])
