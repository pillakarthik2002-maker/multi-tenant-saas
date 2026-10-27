from rest_framework import serializers

from .models import (
    Attachment,
    AuditEvent,
    Board,
    Comment,
    Membership,
    Sprint,
    Task,
    Workflow,
)


ROLE_LEVEL = {
    "viewer": 0,
    "member": 1,
    "admin": 2,
    "owner": 3,
}


class BoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Board
        fields = ("id", "name", "description", "created_at")
        read_only_fields = ("id", "created_at")


class SprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sprint
        fields = ("id", "board", "name", "starts_on", "ends_on", "active")
        read_only_fields = ("id",)

    def validate_board(self, board):
        tenant = self.context["request"].membership.tenant
        if board.tenant_id != tenant.id:
            raise serializers.ValidationError(
                "Board is not in this workspace."
            )
        return board


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            "id",
            "board",
            "sprint",
            "title",
            "description",
            "status",
            "priority",
            "assignee",
            "position",
            "due_date",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        request = self.context["request"]
        tenant = request.membership.tenant
        current = self.instance

        board = attrs.get("board", current.board if current else None)
        sprint = attrs.get("sprint", current.sprint if current else None)
        assignee = attrs.get(
            "assignee",
            current.assignee if current else None,
        )

        if board and board.tenant_id != tenant.id:
            raise serializers.ValidationError({
                "board": "Board is not in this workspace."
            })

        if sprint:
            if sprint.tenant_id != tenant.id:
                raise serializers.ValidationError({
                    "sprint": "Sprint is not in this workspace."
                })
            if board and sprint.board_id != board.id:
                raise serializers.ValidationError({
                    "sprint": "Sprint must belong to the selected board."
                })

        if assignee and not Membership.objects.filter(
            tenant=tenant,
            user=assignee,
        ).exists():
            raise serializers.ValidationError({
                "assignee": "Assignee must be a member of this workspace."
            })

        if current:
            new_status = attrs.get("status", current.status)

            if new_status != current.status:
                has_workflows = Workflow.objects.filter(
                    tenant=tenant
                ).exists()

                if has_workflows:
                    workflow = Workflow.objects.filter(
                        tenant=tenant,
                        from_status=current.status,
                        to_status=new_status,
                    ).first()

                    if not workflow:
                        raise serializers.ValidationError({
                            "status": (
                                "This status transition is not configured."
                            )
                        })

                    user_role = request.membership.role
                    if ROLE_LEVEL[user_role] < ROLE_LEVEL[workflow.allowed_role]:
                        raise serializers.ValidationError({
                            "status": (
                                "Your role cannot perform this transition."
                            )
                        })

        return attrs


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(
        source="author.username",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Comment
        fields = ("id", "body", "author_name", "created_at")
        read_only_fields = ("id", "author_name", "created_at")


class AuditSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(
        source="actor.username",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = AuditEvent
        fields = (
            "id",
            "actor_name",
            "action",
            "object_type",
            "object_id",
            "details",
            "created_at",
        )


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(
        source="uploaded_by.username",
        read_only=True,
    )

    class Meta:
        model = Attachment
        fields = ("id", "file", "uploaded_by_name", "created_at")
        read_only_fields = ("id", "uploaded_by_name", "created_at")


class WorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workflow
        fields = (
            "id",
            "name",
            "from_status",
            "to_status",
            "allowed_role",
            "created_at",
        )
        read_only_fields = ("id", "created_at")