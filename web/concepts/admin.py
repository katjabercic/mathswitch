from django.contrib import admin

from .models import Item


class ItemAdmin(admin.ModelAdmin):
    list_display = ["source", "identifier", "name"]
    search_fields = ["identifier", "name"]
    list_filter = ["source"]


admin.site.register(Item, ItemAdmin)
