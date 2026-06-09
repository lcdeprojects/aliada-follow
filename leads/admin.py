from django.contrib import admin
from .models import Lead, Message, StatusHistory

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('direction', 'content', 'created_at')
    can_delete = False

class StatusHistoryInline(admin.TabularInline):
    model = StatusHistory
    extra = 0
    readonly_fields = ('old_status', 'new_status', 'changed_at', 'changed_by')
    can_delete = False

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'status', 'last_interaction', 'created_at')
    list_filter = ('status', 'created_at', 'last_interaction')
    search_fields = ('name', 'phone')
    inlines = [MessageInline, StatusHistoryInline]
    readonly_fields = ('last_interaction', 'created_at', 'updated_at')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('lead', 'direction', 'created_at', 'content_preview')
    list_filter = ('direction', 'created_at')
    search_fields = ('lead__name', 'lead__phone', 'content')
    readonly_fields = ('lead', 'direction', 'content', 'created_at')

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Conteúdo"

@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('lead', 'old_status', 'new_status', 'changed_at', 'changed_by')
    list_filter = ('old_status', 'new_status', 'changed_at')
    search_fields = ('lead__name', 'lead__phone')
    readonly_fields = ('lead', 'old_status', 'new_status', 'changed_at', 'changed_by')
