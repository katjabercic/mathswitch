from django.contrib import admin

from .models import CategorizerResult, Item


class ItemAdmin(admin.ModelAdmin):
    list_display = ["source", "identifier", "name"]
    search_fields = ["identifier", "name"]
    list_filter = ["source"]


class CategorizerResultAdmin(admin.ModelAdmin):
    list_display = [
        "item",
        "llm_type",
        "result_answer",
        "result_confidence",
        "created_at",
    ]
    search_fields = ["item__name", "item__identifier"]
    list_filter = ["llm_type", "result_answer", "created_at"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]


admin.site.register(Item, ItemAdmin)
admin.site.register(CategorizerResult, CategorizerResultAdmin)
