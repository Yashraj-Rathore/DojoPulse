import json
from pathlib import Path

import pytest
from django.core.management import call_command

from backend.core.models import DefinitionVersion


@pytest.mark.django_db
def test_historical_knowledge_is_pinned_and_loader_idempotent():
    call_command("load_contracts")
    snapshots = dict(DefinitionVersion.objects.values_list("key", "content_hash"))
    call_command("load_contracts")
    assert snapshots == dict(DefinitionVersion.objects.values_list("key", "content_hash"))
    assert DefinitionVersion.objects.filter(kind="drill").count() == 1
    assert not DefinitionVersion.objects.filter(status="APPROVED").exists()
    knowledge = json.loads(Path("game_data/tekken8-3.02.01-pilot-draft.json").read_text())
    assert knowledge["game_build"] == "3.02.01"
