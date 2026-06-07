
from django.contrib import admin

from .models import (
    ActivityLog,
    AIChatMessage,
    AIInteraction,
    Board,
    Card,
    CardAttachment,
    CardLogEntry,
    Column,

    Subtask,
    Swimlane,
    TwoFactorCode,
    UserProfile,
)


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display  = ['name', 'owner', 'created_at', 'updated_at']
    search_fields = ['name', 'owner__username', 'owner__email']
    list_filter   = ['created_at']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields   = ['owner']


@admin.register(Column)
class ColumnAdmin(admin.ModelAdmin):
    list_display  = ['name', 'board', 'position', 'color']
    search_fields = ['name', 'board__name', 'board__owner__username']
    list_filter   = ['board']
    raw_id_fields = ['board']


@admin.register(Swimlane)
class SwimlaneAdmin(admin.ModelAdmin):
    list_display  = ['name', 'board', 'position', 'height']
    search_fields = ['name', 'board__name', 'board__owner__username']
    raw_id_fields = ['board']


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display    = ['title', 'column', 'swimlane', 'priority', 'position', 'created_at']
    search_fields   = ['title', 'description', 'column__board__owner__username']
    list_filter     = ['priority', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields   = ['column', 'swimlane']


@admin.register(Subtask)
class SubtaskAdmin(admin.ModelAdmin):
    list_display  = ['title', 'card', 'is_complete', 'due_date', 'created_at']
    search_fields = ['title', 'card__title', 'card__column__board__owner__username']
    list_filter   = ['is_complete', 'due_date']
    raw_id_fields = ['card']


@admin.register(CardLogEntry)
class CardLogEntryAdmin(admin.ModelAdmin):
    list_display  = ['card', 'source', 'created_at']
    search_fields = ['card__title', 'text']
    list_filter   = ['source', 'created_at']
    readonly_fields = ['created_at']
    raw_id_fields = ['card']


@admin.register(CardAttachment)
class CardAttachmentAdmin(admin.ModelAdmin):
    list_display  = ['filename', 'card', 'file_type', 'file_size', 'upload_date']
    search_fields = ['filename', 'card__title']
    list_filter   = ['file_type', 'upload_date']
    readonly_fields = ['upload_date']
    raw_id_fields   = ['card']


@admin.register(AIChatMessage)
class AIChatMessageAdmin(admin.ModelAdmin):
    list_display  = ['card', 'role', 'created_at']
    search_fields = ['card__title', 'content']
    list_filter   = ['role', 'created_at']
    readonly_fields = ['created_at']
    raw_id_fields   = ['card']


@admin.register(AIInteraction)
class AIInteractionAdmin(admin.ModelAdmin):
    list_display  = ['card', 'created_at']
    search_fields = ['card__title', 'question', 'response']
    list_filter   = ['created_at']
    readonly_fields = ['created_at']
    raw_id_fields   = ['card']


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display  = ['content_type', 'object_id', 'action_type', 'user', 'created_at']
    search_fields = ['action_type', 'message', 'user__username']
    list_filter   = ['action_type', 'content_type', 'created_at']
    readonly_fields = ['content_type', 'object_id', 'created_at']
    raw_id_fields   = ['user']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'plan', 'stripe_subscription_status', 'ai_model', 'two_factor_enabled', 'premium_start_date']
    search_fields = ['user__username', 'user__email', 'stripe_customer_id']
    list_filter   = ['plan', 'stripe_subscription_status', 'two_factor_enabled']
    readonly_fields = ['stripe_customer_id', 'stripe_subscription_id', 'premium_start_date']
    raw_id_fields   = ['user']


@admin.register(TwoFactorCode)
class TwoFactorCodeAdmin(admin.ModelAdmin):
    list_display  = ['user', 'used', 'created_at', 'expires_at']
    search_fields = ['user__username', 'user__email']
    list_filter   = ['used', 'created_at']
    readonly_fields = ['code', 'created_at', 'expires_at']
    raw_id_fields   = ['user']
