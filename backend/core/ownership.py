"""Local transaction order: owner first, then assets/runs/matches/plans.

One owner lock serializes conclusion publication with evidence deletion. This deliberately
trades per-player write concurrency for a simple, auditable pilot invariant.
"""

from django.contrib.auth import get_user_model
from django.db import connection


def lock_owner(owner_id):
    # Serialize owner writes without blocking FK checks for shared review records at
    # another transaction's commit. User primary keys are never rewritten by services.
    return (
        get_user_model()
        .objects.select_for_update(no_key=connection.vendor == "postgresql")
        .get(pk=owner_id)
    )
