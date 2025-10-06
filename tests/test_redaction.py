import os

from qwen_agent.utils.redaction import redact


def test_redact_masks_known_values(tmp_path, monkeypatch):
    secrets_dir = tmp_path / 'secrets'
    secrets_dir.mkdir()
    (secrets_dir / 'API.env').write_text('KEY=ABCDEF1234567890\n', encoding='utf-8')
    monkeypatch.setenv('NOVA_SECRETS_DIR', str(secrets_dir))

    masked = redact('Token ABCDEF1234567890 should be hidden')
    assert 'ABCDEF1234567890' not in masked
    assert 'ABC' in masked and '7890' in masked
