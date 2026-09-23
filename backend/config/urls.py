from django.contrib import admin
from django.urls import path

from backend.core import api, experience_api, match_api, recording_api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/session", api.session),
    path("api/overview", api.overview),
    path("api/preferences", experience_api.preferences),
    path("api/evidence", experience_api.evidence),
    path("api/feedback", experience_api.feedback),
    path("api/notices", experience_api.notices),
    path("api/account/export", experience_api.export_account),
    path("api/account", experience_api.remove_account),
    path("api/match-providers", match_api.providers),
    path("api/player-candidates", match_api.candidates),
    path("api/player-identities", match_api.identities),
    path("api/player-identities/<uuid:identity_id>", match_api.unlink_identity),
    path("api/player-identities/<uuid:identity_id>/sync", match_api.sync_identity),
    path("api/match-syncs/<uuid:sync_id>", match_api.sync_detail),
    path("api/matches", match_api.history),
    path("api/matches/<uuid:match_id>", match_api.remove_match),
    path("api/matches/<uuid:match_id>/recordings", recording_api.upload_recording),
    path(
        "api/matches/<uuid:match_id>/recordings/<uuid:source_id>/reprocess", recording_api.reprocess
    ),
    path("api/uploads", api.upload),
    path("api/runs/<uuid:run_id>", api.run_detail),
    path("api/assets/<uuid:asset_id>", api.asset_delete),
    path("api/assets/<uuid:asset_id>/media", api.media),
    path("api/assignments", api.assignments),
    path("api/plans", api.plans),
    path("api/assignments/<uuid:assignment_id>/practice", api.practice),
    path("api/plans/<uuid:plan_id>/evaluate", api.evaluations),
]
