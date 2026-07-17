from django.contrib import admin
from .models import Task, Comment, ActivityLog, Attachment

admin.site.register(Task)
admin.site.register(Comment)
admin.site.register(ActivityLog)
admin.site.register(Attachment)