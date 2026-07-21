from django.contrib import admin
from .models import Task, Comment, ActivityLog, Attachment, TimeEntry, SearchDocument


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'status', 'priority', 'assigned_to', 'due_date']
    search_fields = ['title', 'project__name']
    list_filter = ['status', 'priority']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['task', 'author', 'created_at']
    search_fields = ['task__title', 'author__username']


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['task', 'action', 'actor', 'created_at']
    list_filter = ['action']


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'task', 'uploaded_by', 'uploaded_at']


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ['task', 'user', 'started_at', 'ended_at']
    list_filter = ['user']


@admin.register(SearchDocument)
class SearchDocumentAdmin(admin.ModelAdmin):
    list_display = ['content_type', 'object_id', 'project', 'updated_at']
    list_filter = ['content_type']