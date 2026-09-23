import json
from pathlib import Path

from django.core.management.base import BaseCommand

from backend.core.models import Character, DefinitionVersion, Game, GameBuild, Move

ROOT = Path(__file__).resolve().parents[4]


class Command(BaseCommand):
    help = "Load immutable DRAFT contracts. Does not approve gameplay knowledge or drill."

    def handle(self, *args, **options):
        game, _ = Game.objects.get_or_create(key="tekken8")
        build, _ = GameBuild.objects.get_or_create(
            key="tekken8/steam/3.02.01",
            defaults={
                "game": game,
                "platform": "steam",
                "verified": False,
                "provenance": {
                    "url": "https://www.bandainamcoent.com/news/tekken-8-patch-notes-v3-02-01"
                },
            },
        )
        character, _ = Character.objects.get_or_create(key="jin", defaults={"game": game})
        for key in ("jin.uf4", "jin.24"):
            Move.objects.get_or_create(key=key, defaults={"character": character})
        for filename, kind in [
            ("contracts/capture-profile-v1.json", "capture"),
            ("contracts/situation-v1.json", "situation"),
            ("contracts/drill-v1.json", "drill"),
            ("game_data/tekken8-3.02.01-pilot-draft.json", "knowledge"),
        ]:
            payload = json.loads((ROOT / filename).read_text(encoding="utf-8"))
            DefinitionVersion.objects.get_or_create(
                key=payload["id"],
                defaults={
                    "kind": kind,
                    "game_build": build,
                    "status": "DRAFT",
                    "payload": payload,
                },
            )
        DefinitionVersion.objects.get_or_create(
            key="punish-success/v1",
            defaults={
                "kind": "metric",
                "game_build": build,
                "status": "DRAFT",
                "payload": {
                    "numerator": "verified qualifying punish",
                    "denominator": "eligible opportunities with known outcomes",
                    "minimum_sample": 40,
                    "minimum_sessions": 5,
                },
            },
        )
        self.stdout.write("Draft contracts loaded; no release gates changed.")
