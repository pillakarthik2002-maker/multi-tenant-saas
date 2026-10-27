from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import FormParser, MultiPartParser
from .models import AuditEvent, Board, Comment, Sprint, Task, Attachment, Workflow
from .permissions import TenantMembershipRequired
from .serializers import (
    AuditSerializer,
    BoardSerializer,
    CommentSerializer,
    SprintSerializer,
    TaskSerializer,
    AttachmentSerializer,
    WorkflowSerializer
)


def require_write_access(request):
    if request.membership.role == "viewer":
        raise PermissionDenied("Viewer role cannot make changes.")


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
        AuditEvent.objects.create(
            tenant=self.request.membership.tenant,
            actor=self.request.user,
            action="task.updated",
            object_type="Task",
            object_id=task.id,
            details={
                "old_status": old_status,
                "new_status": task.status,
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
            pk=self.kwargs["pk"],
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
            tenant=self.request.membership.tenant,
            task=task,
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
    parser_classes = [MultiPartParser, FormParser]

    def get_task(self):
        return get_object_or_404(
            Task,
            pk=self.kwargs["pk"],
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
            tenant=self.request.membership.tenant,
            task=task,
            uploaded_by=self.request.user,
        )
        AuditEvent.objects.create(
            tenant=self.request.membership.tenant,
            actor=self.request.user,
            action="attachment.created",
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
            raise PermissionDenied("Only workspace owners and admins can edit workflows.")

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