"""Local transaction order: owner first, then assets/runs/matches/plans.

One owner lock serializes conclusion publication with evidence deletion. This deliberately
trades per-player write concurrency for a simple, auditable pilot invariant.
"""

from django.contrib.auth import get_user_model


def lock_owner(owner_id):
    return get_user_model().objects.select_for_update().get(pk=owner_id)
