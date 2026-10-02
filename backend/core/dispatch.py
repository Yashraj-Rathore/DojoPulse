"""Outbox transport and physical-execution reconciliation, outside HTTP/media parsing."""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from backend.core.cloud import CloudFailure
from backend.core.jobs import acknowledge_stopped, claim_run, locked_run, reconcile_runs
from backend.core.models import ExecutionSlot, RunDispatch


def dispatch_pending(provider, limit=100):
    if settings.RESTORE_QUARANTINE:
        return
    reconcile_runs()
    now = timezone.now()
    candidates = RunDispatch.objects.filter(
        status__in=["PENDING", "RETRY"], next_attempt_at__lte=now
    )
    for dispatch_id in candidates.order_by("next_attempt_at").values_list("pk", flat=True)[:limit]:
        with transaction.atomic():
            item = RunDispatch.objects.get(pk=dispatch_id)
            run = locked_run(item.run_id)
            item = RunDispatch.objects.select_for_update().get(pk=dispatch_id)
            if run.status != "QUEUED" or item.status not in {"PENDING", "RETRY"}:
                continue
            if item.lease_until and item.lease_until > now:
                continue
            item.attempts += 1
            item.lease_until = now + timedelta(seconds=60)
            item.save()
            generation = item.generation
        try:
            name = provider.enqueue(item.pk, generation)
        except CloudFailure as error:
            with transaction.atomic():
                locked_run(item.run_id)
                current = RunDispatch.objects.select_for_update().get(pk=item.pk)
                if current.generation != generation or current.status not in {"PENDING", "RETRY"}:
                    continue
                current.status = (
                    "RETRY" if error.retryable and current.attempts < 8 else "ATTENTION"
                )
                current.error_code, current.lease_until = error.code, None
                current.next_attempt_at = timezone.now() + timedelta(
                    seconds=min(300, 2**current.attempts)
                )
                current.save()
        else:
            with transaction.atomic():
                locked_run(item.run_id)
                # Handler may already have started. Never regress its state.
                RunDispatch.objects.filter(
                    pk=item.pk, generation=generation, status__in=["PENDING", "RETRY"]
                ).update(status="ENQUEUED", task_name=name, lease_until=None, error_code="")


def launch_dispatch(provider, dispatch_id, generation):
    if settings.RESTORE_QUARANTINE:
        raise CloudFailure("RESTORE_QUARANTINE", retryable=False)
    if not settings.CLOUD_MEDIA_RUNTIME_QUALIFIED:
        raise CloudFailure("CLOUD_MEDIA_RUNTIME_UNQUALIFIED", retryable=False)
    with transaction.atomic():
        item = RunDispatch.objects.get(pk=dispatch_id)
        run = locked_run(item.run_id)
        item = RunDispatch.objects.select_for_update().get(pk=dispatch_id)
        if item.generation != generation or run.status != "QUEUED":
            return "IGNORED"
        if item.status not in {"PENDING", "RETRY", "ENQUEUED"}:
            return "IGNORED"
        fence = claim_run(run.pk)
        if fence is None:
            return "CAPACITY"
        item.status, item.lease_until = "LAUNCHING", timezone.now() + timedelta(seconds=60)
        item.save()
        ExecutionSlot.objects.filter(run=run, fence=fence).update(runtime="CLOUD_RUN")
    # LAUNCHING is durable before the RPC. Crash/timeout never triggers another launch.
    try:
        operation = provider.launch(run.pk, fence, item.pk, generation)
    except CloudFailure as error:
        with transaction.atomic():
            locked_run(run.pk)
            RunDispatch.objects.filter(
                pk=item.pk, generation=generation, status="LAUNCHING"
            ).update(
                status="UNCERTAIN" if error.ambiguous else "ATTENTION",
                error_code=error.code,
                lease_until=None,
            )
        if not error.ambiguous:
            acknowledge_stopped(run.pk, fence)  # Explicit rejection means no execution was created.
            RunDispatch.objects.filter(pk=item.pk).update(status="ATTENTION", error_code=error.code)
        return "UNCERTAIN" if error.ambiguous else "ATTENTION"
    with transaction.atomic():
        locked_run(run.pk)
        # Save the receipt even if cancellation/worker-start raced with the response.
        RunDispatch.objects.filter(pk=item.pk, generation=generation).update(
            operation_name=operation
        )
        RunDispatch.objects.filter(pk=item.pk, generation=generation, status="LAUNCHING").update(
            status="SUBMITTED", lease_until=None
        )
    return "SUBMITTED"


def reconcile_cloud(provider):
    reconcile_runs()
    now = timezone.now()
    RunDispatch.objects.filter(status="LAUNCHING", lease_until__lte=now).update(
        status="UNCERTAIN", lease_until=None
    )
    for slot in ExecutionSlot.objects.filter(runtime="CLOUD_RUN", released_at=None).select_related(
        "run"
    )[:100]:
        dispatch = RunDispatch.objects.get(run=slot.run)
        try:
            name = slot.execution_name
            if not name and dispatch.operation_name:
                name = provider.observe_operation(dispatch.operation_name)
                if name:
                    ExecutionSlot.objects.filter(pk=slot.pk, released_at=None).update(
                        execution_name=name
                    )
            if not name:
                continue  # Missing receipt requires an audited runtime inventory/operator resolution.
            if slot.stop_requested_at:
                provider.cancel(name)
            if provider.execution_stopped(name):
                acknowledge_stopped(slot.run_id, slot.fence)
        except CloudFailure:
            continue  # Outage never frees capacity or publishes results.
