from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from .views import (
    AuditList,
    BoardList,
    CurrentWorkspaceView,
    HealthView,
    SprintList,
    TaskComments,
    TaskDetail,
    TaskList,
    TaskAttachments,
    WorkflowList
)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("token/", obtain_auth_token, name="api-token"),
    path("workspace/", CurrentWorkspaceView.as_view(), name="current-workspace"),
    path("boards/", BoardList.as_view(), name="board-list"),
    path("sprints/", SprintList.as_view(), name="sprint-list"),
    path("tasks/", TaskList.as_view(), name="task-list"),
    path("tasks/<int:pk>/", TaskDetail.as_view(), name="task-detail"),
    path("tasks/<int:pk>/comments/", TaskComments.as_view(), name="task-comments"),
    path("audit/", AuditList.as_view(), name="audit-list"),
    path("tasks/<int:pk>/attachments/",TaskAttachments.as_view(),name="task-attachments",),
    path("workflows/", WorkflowList.as_view(), name="workflow-list"),
]