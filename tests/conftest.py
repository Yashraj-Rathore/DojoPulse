import pytest


@pytest.fixture(autouse=True)
def isolated_control_journal(settings, tmp_path):
    # Restored/reused test user IDs must never share a journal with another test.
    settings.CONTROL_JOURNAL_ROOT = tmp_path / "control-journal"
    settings.CONTROL_JOURNAL_KEY = "test-journal-key"
    settings.PREVIEW_LEDGER_ROOT = tmp_path / "preview-writes"
    settings.PREVIEW_LEDGER_KEY = "test-preview-ledger-key"
    from django.test import override_settings

    from backend.core.preview_ledger import FileLedger

    settings.PREVIEW_LEDGER_RUNTIME_QUALIFIED = True  # Controlled fake-store tests only.
    with override_settings(DEBUG=True):
        FileLedger().initialize()
