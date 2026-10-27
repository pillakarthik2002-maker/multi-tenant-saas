from rest_framework.exceptions import PermissionDenied

from .models import Membership


def get_request_membership(request):
    tenant_id = request.headers.get("X-Tenant-ID")

    if not tenant_id:
        raise PermissionDenied("X-Tenant-ID header is required.")

    try:
        return Membership.objects.select_related("tenant").get(
            tenant_id=tenant_id,
            user=request.user,
        )
    except Membership.DoesNotExist:
        raise PermissionDenied("You are not a member of this workspace.")


class TenantMembershipRequired:
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        request.membership = get_request_membership(request)