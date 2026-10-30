from celery import shared_task
from django.db.models import Count

from .models import Task


@shared_task
def build_weekly_report(tenant_id):
    return list(
        Task.objects.filter(tenant_id=tenant_id)
        .values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )