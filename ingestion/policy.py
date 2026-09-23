"""Pure operation gating and retry scheduling; never performs or sleeps on a request."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from ingestion.contracts import Operation, ProviderClass, require_aware


@dataclass(frozen=True)
class ProviderPolicy:
    key: str
    access_class: ProviderClass
    capabilities: frozenset[Operation]
    enabled_operations: frozenset[Operation] = frozenset()
    technical_review: str | None = None
    usage_review: str | None = None
    approved_purpose: str | None = None
    approval_expires_at: datetime | None = None
    reverse_engineering_decision: str | None = None


def require_operation(
    policy: ProviderPolicy, operation: Operation, purpose: str, now: datetime
) -> None:
    require_aware(now)
    if operation not in policy.capabilities:
        raise PermissionError("OPERATION_UNSUPPORTED")
    if operation not in policy.enabled_operations:
        raise PermissionError("OPERATION_DISABLED")
    if not policy.technical_review or not policy.usage_review or purpose != policy.approved_purpose:
        raise PermissionError("PURPOSE_REVIEW_REQUIRED")
    if policy.approval_expires_at is None:
        raise PermissionError("APPROVAL_EXPIRY_REQUIRED")
    require_aware(policy.approval_expires_at)
    if policy.approval_expires_at <= now:
        raise PermissionError("APPROVAL_EXPIRED")
    if (
        policy.access_class == ProviderClass.REVERSE_ENGINEERED
        and not policy.reverse_engineering_decision
    ):
        raise PermissionError("EXPLICIT_REVERSE_ENGINEERING_REVIEW_REQUIRED")


@dataclass(frozen=True)
class RetryDecision:
    action: str
    not_before: datetime | None


def retry_decision(
    status: int | None,
    attempt: int,
    now: datetime,
    *,
    retry_after: str | None = None,
    jitter_fraction: float = 0.5,
    max_attempts: int = 5,
) -> RetryDecision:
    """status=None means a transport timeout; schema errors never use this retry function."""
    require_aware(now)
    if attempt < 1 or max_attempts < 1 or not 0 <= jitter_fraction <= 1:
        raise ValueError("Invalid retry policy")
    if status in {401, 403}:
        return RetryDecision("REVIEW_AUTH_OR_PERMISSION", None)
    if status == 404:
        return RetryDecision("NOT_FOUND", None)
    if status == 410:
        return RetryDecision("EXPIRED_IF_PROVIDER_CONTRACT_CONFIRMS", None)
    if status is not None and 200 <= status < 300:
        return RetryDecision("ACCEPT", None)
    if status is not None and status != 429 and not 500 <= status < 600:
        return RetryDecision("DO_NOT_RETRY", None)
    if attempt >= max_attempts:
        return RetryDecision("RETRY_BUDGET_EXHAUSTED", None)
    seconds = min(300, 2 ** min(attempt, 12)) * (0.5 + 0.5 * jitter_fraction)
    deadline = now + timedelta(seconds=seconds)
    if retry_after:
        try:
            if retry_after.isascii() and retry_after.isdecimal():
                requested = now + timedelta(seconds=int(retry_after))
            else:
                requested = parsedate_to_datetime(retry_after)
                require_aware(requested)
        except (ValueError, TypeError, OverflowError):
            # Missing/unparseable provider cooldown needs review, not an early request.
            return RetryDecision("INVALID_RETRY_AFTER_REVIEW", None)
        deadline = max(deadline, requested)
    return RetryDecision("RETRY", deadline)
