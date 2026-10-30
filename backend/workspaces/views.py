from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

import stripe

from .models import (
    Attachment,
    AuditEvent,
    Board,
    Comment,
    Sprint,
    Task,
    Tenant,
    Workflow,
)
from .permissions import TenantMembershipRequired
from .serializers import (
    AttachmentSerializer,
    AuditSerializer,
    BoardSerializer,
    CommentSerializer,
    SprintSerializer,
    TaskSerializer,
    WorkflowSerializer,
)
from .tasks import build_weekly_report


FREE_PLAN_LIMITS = {
    "boards": 1,
    "tasks": 10,
}


def require_write_access(request):
    if request.membership.role == "viewer":
        raise PermissionDenied("Viewer role cannot make changes.")


def enforce_plan_limit(request, resource):
    tenant = request.membership.tenant

    if tenant.subscription_status == "active":
        return

    limit = FREE_PLAN_LIMITS[resource]

    if resource == "boards":
        current_count = Board.objects.filter(tenant=tenant).count()
    elif resource == "tasks":
        current_count = Task.objects.filter(tenant=tenant).count()
    else:
        return

    if current_count >= limit:
        raise PermissionDenied(
            f"Free plan allows up to {limit} {resource}. "
            "Upgrade to Pro for more."
        )


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok", "service": "workspace-api"})


class CurrentWorkspaceView(TenantMembershipRequired, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        membership = request.membership
        return Response({
            "id": membership.tenant_id,
            "name": membership.tenant.name,
            "slug": membership.tenant.slug,
            "role": membership.role,
        })


class BoardList(TenantMembershipRequired, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BoardSerializer

    def get_queryset(self):
        return Board.objects.filter(tenant=self.request.membership.tenant)

    def perform_create(self, serializer):
        require_write_access(self.request)
        enforce_plan_limit(self.request, "boards")

        board = serializer.save(
            tenant=self.request.membership.tenant,
            created_by=self.request.user,
        )
        AuditEvent.objects.create(
            tenant=self.request.membership.tenant,
            actor=self.request.user,
            action="board.created",
            object_type="Board",
            object_id=board.id,
        )


class SprintList(TenantMembershipRequired, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SprintSerializer

    def get_queryset(self):
        return Sprint.objects.filter(tenant=self.request.membership.tenant)

    def perform_create(self, serializer):
        require_write_access(self.request)

        sprint = serializer.save(tenant=self.request.membership.tenant)
        AuditEvent.objects.create(
            tenant=self.request.membership.tenant,
            actor=self.request.user,
            action="sprint.created",
            object_type="Sprint",
            object_id=sprint.id,
        )


class TaskList(TenantMembershipRequired, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer

    def get_queryset(self):
        queryset = Task.objects.filter(
            tenant=self.request.membership.tenant
        ).select_related("board", "sprint", "assignee")

        board_id = self.request.query_params.get("board")
        if board_id:
            queryset = queryset.filter(board_id=board_id)

        return queryset.order_by("status", "position")

    def perform_create(self, serializer):
        require_write_access(self.request)
        enforce_plan_limit(self.request, "tasks")

        task = serializer.save(tenant=self.request.membership.tenant)
        AuditEvent.objects.create(
            tenant=self.request.membership.tenant,
            actor=self.request.user,
            action="task.created",
            object_type="Task",
            object_id=task.id,
        )


class TaskDetail(TenantMembershipRequired, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.filter(
            tenant=self.request.membership.tenant
        ).select_related("board", "sprint", "assignee")

    def perform_update(self, serializer):
        require_write_access(self.request)

        old_status = serializer.instance.status
        task = serializer.save()

        if old_status != task.status:
            AuditEvent.objects.create(
                tenant=self.request.membership.tenant,
                actor=self.request.user,
                action="task.status_changed",
                object_type="Task",
                object_id=task.id,
                details={
                    "from": old_status,
                    "to": task.status,
                },
            )

    def perform_destroy(self, instance):
        require_write_access(self.request)

        AuditEvent.objects.create(
            tenant=self.request.membership.tenant,
            actor=self.request.user,
            action="task.deleted",
            object_type="Task",
            object_id=instance.id,
        )
        instance.delete()


class TaskComments(TenantMembershipRequired, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CommentSerializer

    def get_task(self):
        return get_object_or_404(
            Task,
            id=self.kwargs["task_id"],
            tenant=self.request.membership.tenant,
        )

    def get_queryset(self):
        return Comment.objects.filter(
            task=self.get_task(),
            tenant=self.request.membership.tenant,
        ).select_related("author")

    def perform_create(self, serializer):
        require_write_access(self.request)
        task = self.get_task()

        comment = serializer.save(
            task=task,
            tenant=self.request.membership.tenant,
            author=self.request.user,
        )
        AuditEvent.objects.create(
            tenant=self.request.membership.tenant,
            actor=self.request.user,
            action="comment.created",
            object_type="Task",
            object_id=task.id,
            details={"comment_id": comment.id},
        )


class AuditList(TenantMembershipRequired, generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AuditSerializer

    def get_queryset(self):
        return AuditEvent.objects.filter(
            tenant=self.request.membership.tenant
        ).select_related("actor")


class TaskAttachments(TenantMembershipRequired, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AttachmentSerializer

    def get_task(self):
        return get_object_or_404(
            Task,
            id=self.kwargs["task_id"],
            tenant=self.request.membership.tenant,
        )

    def get_queryset(self):
        return Attachment.objects.filter(
            task=self.get_task(),
            tenant=self.request.membership.tenant,
        ).select_related("uploaded_by")

    def perform_create(self, serializer):
        require_write_access(self.request)
        task = self.get_task()

        attachment = serializer.save(
            task=task,
            tenant=self.request.membership.tenant,
            uploaded_by=self.request.user,
        )
        AuditEvent.objects.create(
            tenant=self.request.membership.tenant,
            actor=self.request.user,
            action="attachment.uploaded",
            object_type="Task",
            object_id=task.id,
            details={"attachment_id": attachment.id},
        )


class WorkflowList(TenantMembershipRequired, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkflowSerializer

    def get_queryset(self):
        return Workflow.objects.filter(
            tenant=self.request.membership.tenant
        )

    def perform_create(self, serializer):
        if self.request.membership.role not in ("owner", "admin"):
            raise PermissionDenied(
                "Only workspace owners and admins can edit workflows."
            )

        workflow = serializer.save(
            tenant=self.request.membership.tenant
        )
        AuditEvent.objects.create(
            tenant=self.request.membership.tenant,
            actor=self.request.user,
            action="workflow.created",
            object_type="Workflow",
            object_id=workflow.id,
        )


class WeeklyReportTrigger(TenantMembershipRequired, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        require_write_access(request)

        job = build_weekly_report.delay(request.membership.tenant_id)
        return Response({
            "task_id": job.id,
            "status": "PENDING",
        })


class CreateCheckoutSessionView(TenantMembershipRequired, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.membership.role not in ("owner", "admin"):
            raise PermissionDenied(
                "Only workspace owners and admins can manage billing."
            )

        if not settings.STRIPE_SECRET_KEY:
            return Response(
                {"detail": "Stripe is not configured."},
                status=503,
            )

        stripe.api_key = settings.STRIPE_SECRET_KEY
        tenant = request.membership.tenant

        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{
                "price_data": {
                    "currency": "inr",
                    "product_data": {"name": "Pro Workspace"},
                    "unit_amount": 49900,
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }],
            success_url=(
                "http://localhost:5173/"
                "?billing=success&session_id={CHECKOUT_SESSION_ID}"
            ),
            cancel_url="http://localhost:5173/?billing=cancel",
            client_reference_id=str(tenant.id),
            metadata={"tenant_id": str(tenant.id)},
            subscription_data={
                "metadata": {"tenant_id": str(tenant.id)}
            },
        )

        return Response({"url": session.url})


class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        if not webhook_secret:
            return Response(
                {"detail": "Stripe webhook is not configured."},
                status=503,
            )

        signature = request.headers.get("Stripe-Signature", "")

        try:
            event = stripe.Webhook.construct_event(
                request.body,
                signature,
                webhook_secret,
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            return Response(
                {"detail": "Invalid Stripe webhook signature."},
                status=400,
            )

        event_type = event["type"]
        stripe_object = event["data"]["object"]

        if hasattr(stripe_object, "to_dict"):
            stripe_object = stripe_object.to_dict()

        metadata = stripe_object.get("metadata") or {}
        tenant_id = (
            metadata.get("tenant_id")
            or stripe_object.get("client_reference_id")
        )

        if not tenant_id:
            return Response({"received": True})

        tenant = Tenant.objects.filter(id=tenant_id).first()
        if tenant is None:
            return Response({"received": True})

        if event_type == "checkout.session.completed":
            tenant.stripe_customer_id = stripe_object.get("customer")
            tenant.stripe_subscription_id = stripe_object.get("subscription")
            tenant.subscription_status = "active"

        elif event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
        ):
            tenant.stripe_customer_id = stripe_object.get("customer")
            tenant.stripe_subscription_id = stripe_object.get("id")
            tenant.subscription_status = stripe_object.get("status", "inactive")

        elif event_type == "customer.subscription.deleted":
            tenant.stripe_subscription_id = stripe_object.get("id")
            tenant.subscription_status = "canceled"

        else:
            return Response({"received": True})

        tenant.save(update_fields=[
            "stripe_customer_id",
            "stripe_subscription_id",
            "subscription_status",
        ])
        return Response({"received": True})


class BillingStatusView(TenantMembershipRequired, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = request.membership.tenant
        has_pro_access = tenant.subscription_status == "active"

        return Response({
            "plan": "Pro Workspace" if has_pro_access else "Free",
            "status": tenant.subscription_status,
            "has_pro_access": has_pro_access,
        })