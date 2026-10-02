import pytest


@pytest.fixture(autouse=True)
def isolated_control_journal(settings, tmp_path):
    # Restored/reused test user IDs must never share a journal with another test.
    settings.CONTROL_JOURNAL_ROOT = tmp_path / "control-journal"
    settings.CONTROL_JOURNAL_KEY = "test-journal-key"
