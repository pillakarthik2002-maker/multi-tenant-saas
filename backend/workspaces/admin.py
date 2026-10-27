from django.contrib import admin

from .models import Board, Membership, Sprint, Task, Tenant, Comment, AuditEvent, Attachment, Workflow

admin.site.register(Tenant)
admin.site.register(Membership)
admin.site.register(Board)
admin.site.register(Sprint)
admin.site.register(Task)
admin.site.register(Comment)
admin.site.register(AuditEvent)
admin.site.register(Attachment)
admin.site.register(Workflow)