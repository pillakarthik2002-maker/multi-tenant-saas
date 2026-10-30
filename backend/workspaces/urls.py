from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from .views import (
    AuditList,
    BillingStatusView,
    BoardList,
    CreateCheckoutSessionView,
    CurrentWorkspaceView,
    HealthView,
    SprintList,
    StripeWebhookView,
    TaskAttachments,
    TaskComments,
    TaskDetail,
    TaskList,
    WeeklyReportTrigger,
    WorkflowList,
)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("token/", obtain_auth_token, name="api-token"),
    path("workspace/", CurrentWorkspaceView.as_view(), name="current-workspace"),

    path("boards/", BoardList.as_view(), name="board-list"),
    path("sprints/", SprintList.as_view(), name="sprint-list"),
    path("tasks/", TaskList.as_view(), name="task-list"),
    path("tasks/<int:pk>/", TaskDetail.as_view(), name="task-detail"),
    path(
        "tasks/<int:task_id>/comments/",
        TaskComments.as_view(),
        name="task-comments",
    ),
    path(
        "tasks/<int:task_id>/attachments/",
        TaskAttachments.as_view(),
        name="task-attachments",
    ),

    path("audit/", AuditList.as_view(), name="audit-list"),
    path("workflows/", WorkflowList.as_view(), name="workflow-list"),
    path(
        "reports/weekly/",
        WeeklyReportTrigger.as_view(),
        name="weekly-report",
    ),

    path(
        "billing/checkout/",
        CreateCheckoutSessionView.as_view(),
        name="billing-checkout",
    ),
    path(
        "billing/webhook/",
        StripeWebhookView.as_view(),
        name="stripe-webhook",
    ),
    path(
        "billing/status/",
        BillingStatusView.as_view(),
        name="billing-status",
    ),
]
