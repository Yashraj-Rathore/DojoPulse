from django.db import migrations, models


def populate_keys(apps, schema_editor):
    Attempt = apps.get_model("core", "DrillAttempt")
    for attempt in Attempt.objects.select_related("source_event"):
        attempt.played_key = f"{attempt.source_event.match_id}:{attempt.source_event.played_key}"
        attempt.save(update_fields=["played_key"])


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [
        migrations.AddField(model_name="drillattempt", name="played_key",
                            field=models.CharField(max_length=240, null=True)),
        migrations.RunPython(populate_keys, migrations.RunPython.noop),
        migrations.AlterField(model_name="drillattempt", name="played_key",
                              field=models.CharField(max_length=240, unique=True)),
    ]
