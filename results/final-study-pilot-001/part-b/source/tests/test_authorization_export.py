import hashlib
import io
from pathlib import Path
import zipfile
from dashboard.app import zip_sanitized


def exported(path):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as archive:
        exported_hash, original_hash = zip_sanitized(archive, path, 'source/tests/test_dashboard.py')
    with zipfile.ZipFile(io.BytesIO(out.getvalue())) as archive:
        return archive.read('source/tests/test_dashboard.py'), exported_hash, original_hash


def test_reviewed_synthetic_fixture_is_byte_preserved(monkeypatch):
    monkeypatch.delenv('EXAMPLE_API_KEY', raising=False)
    source = Path(__file__).parent/'test_dashboard.py'
    data, changed, original = exported(source)
    assert data == source.read_bytes()
    assert changed == original == hashlib.sha256(data).hexdigest()


def test_known_real_secret_takes_priority_over_reviewed_fixture(monkeypatch):
    monkeypatch.setenv('EXAMPLE_API_KEY', 'sk-test-never-publish-this-secret')
    data, changed, original = exported(Path(__file__).parent/'test_dashboard.py')
    assert b'sk-test-never-publish-this-secret' not in data
    assert changed != original


def test_edited_fixture_cannot_use_verbatim_exception(tmp_path, monkeypatch):
    monkeypatch.setenv('EXAMPLE_API_KEY', 'sk-actual-example-sensitive-value')
    source = tmp_path/'test_dashboard.py'
    source.write_bytes((Path(__file__).parent/'test_dashboard.py').read_bytes()+b'\nkey="sk-actual-example-sensitive-value"\n')
    data, changed, original = exported(source)
    assert b'sk-actual-example-sensitive-value' not in data
    assert changed != original
