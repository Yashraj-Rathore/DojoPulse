from django.contrib import admin

from backend.core.models import (
    AnalysisRun,
    DefinitionVersion,
    EvaluationPlan,
    GameplayEvent,
    ImprovementEvaluation,
    Match,
    Profile,
    ReplayAsset,
)


class ReadOnlyEvidenceAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


for model in (
    AnalysisRun,
    DefinitionVersion,
    EvaluationPlan,
    GameplayEvent,
    ImprovementEvaluation,
    Match,
    ReplayAsset,
):
    admin.site.register(model, ReadOnlyEvidenceAdmin)
admin.site.register(Profile)
