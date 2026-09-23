from django.db import migrations


def backfill(apps, schema_editor):
    Match = apps.get_model("core", "Match")
    ReplaySource = apps.get_model("core", "ReplaySource")
    alias = schema_editor.connection.alias
    for match in Match.objects.using(alias).exclude(asset_id=None).select_related("asset").iterator():
        asset = match.asset
        ReplaySource.objects.using(alias).get_or_create(
            match_id=match.pk, asset_id=asset.pk,
            defaults={
                "provider": "user-video", "access_class": "USER_UPLOAD", "representation": "VIDEO",
                "availability": "NOT_FOUND" if asset.deleted_at else "AVAILABLE",
                "local_retain_until": asset.retain_until, "content_hash": asset.source_sha256,
                "canonical_build": match.game_build,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("core", "0003_provider_neutral_matches")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
