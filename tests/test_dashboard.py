"""Exercise the browser API lifecycle and evidence-preservation boundaries."""
import io
import gzip
import json
from pathlib import Path
import time
import zipfile
import subprocess

from fastapi.testclient import TestClient
import pytest

from dashboard.app import JobManager, create_app


@pytest.fixture
def console(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    results = repo / "results"
    app = create_app(results, repo=repo)
    return TestClient(app, base_url="http://127.0.0.1:8765"), app.state.manager, repo


def wait_finished(client, job_id):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in {"completed", "failed", "cancelled"}:
            return job
        time.sleep(0.02)
    raise AssertionError("Job did not terminate")


def test_complete_workflow_preserves_raw_and_exports_redacted_bundle(console, monkeypatch):
    client, manager, repo = console
    secret = "sk-test-never-publish-this-secret"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    (repo / "testbed").mkdir()
    (repo / "testbed" / "version.py").write_text('VERSION = "export-time"')
    (repo / "README.md").write_text("Export-time additional instructions")
    (repo / "Dockerfile").write_bytes(b"FROM export-time\n")
    (repo / "docs" / "figures").mkdir(parents=True)
    (repo / "docs" / "figures" / "deployed-architecture.mmd").write_bytes(b"flowchart LR\n  agent --> gateway\n")

    def command(job, args, log):
        root = manager.root / job["id"]
        if "testbed.cli" in args:
            run = root / "runs" / "trial-001"
            run.mkdir(parents=True)
            (run / "summary.json").write_text(json.dumps({"condition": "C0", "scenario": "S2", "mode": "scripted", "phase": "engineering", "unauthorized_outcome": True, "api_key": secret}), encoding="utf-8")
            (run / "audit.jsonl").write_text(json.dumps({"action": "email.send", "authorization": "Bearer " + secret}) + "\n", encoding="utf-8")
            (run / "large.log").write_text("x" * (1024 * 1024 - 7) + secret + "y" * (1024 * 1024), encoding="utf-8")
            with gzip.open(run / "audit-0001.jsonl.gz", "wt", encoding="utf-8") as compressed:
                compressed.write(json.dumps({"action": "email.send", "credential": "disposable-bearer-never-export", "api_key": secret}) + "\n")
            (root / "source" / "testbed").mkdir(parents=True)
            (root / "source" / "testbed" / "version.py").write_bytes(b'VERSION = "collection-time"\r\n')
            (root / "source" / "configs").mkdir()
            (root / "source" / "configs" / "example.json").write_bytes(b'{"sample": true}\r\n')
            (root / "source" / "Dockerfile").write_bytes(b"FROM collection-time\r\n")
            log.write(b"runner executed\n")
        else:
            (root / "analysis").mkdir()
            (root / "analysis" / "rates.csv").write_text("condition,n\nC0,1\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(manager, "_command", command)
    response = client.post("/api/jobs", json={"conditions": ["C0"], "scenarios": ["S2"]})
    assert response.status_code == 202
    job_id = response.json()["id"]
    job = wait_finished(client, job_id)
    assert job["status"] == "completed"
    assert job["completed_runs"] == 1
    assert job["evidence_label"] == "SCRIPTED CONTROL CHECK"
    raw = manager.root / job_id / "runs" / "trial-001" / "summary.json"
    original = raw.read_bytes()
    assert secret in raw.read_text()
    assert secret not in client.get(f"/api/jobs/{job_id}/runs").text
    assert secret not in client.get(f"/api/jobs/{job_id}/trace", params={"path": "runs/trial-001/audit.jsonl"}).text
    decoded = client.get(f"/api/jobs/{job_id}/trace", params={"path": "runs/trial-001/audit-0001.jsonl.gz"})
    assert decoded.status_code == 200
    assert "disposable-bearer-never-export" not in decoded.text
    assert json.loads(decoded.text)["action"] == "email.send"
    assert client.get(f"/api/jobs/{job_id}/export.csv").status_code == 200
    assert client.get(f"/api/jobs/{job_id}/export.json").json()[0]["unauthorized_outcome"] is True
    exported = client.get(f"/api/jobs/{job_id}/bundle")
    assert exported.status_code == 200
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert "SHA256SUMS.json" in archive.namelist()
        assert "results/analysis/rates.csv" in archive.namelist()
        assert all(secret.encode() not in archive.read(name) for name in archive.namelist())
        assert archive.read("source/testbed/version.py") == b'VERSION = "collection-time"\r\n'
        assert archive.read("source/configs/example.json") == b'{"sample": true}\r\n'
        assert archive.read("source/Dockerfile") == b"FROM collection-time\r\n"
        assert "export-time-extras/Dockerfile" not in archive.namelist()
        assert archive.read("export-time-extras/docs/figures/deployed-architecture.mmd") == b"flowchart LR\n  agent --> gateway\n"
        assert "export-time-extras/README.md" in archive.namelist()
        decoded_member = gzip.decompress(archive.read("results/runs/trial-001/audit-0001.jsonl.gz"))
        assert secret.encode() not in decoded_member
        assert b"disposable-bearer-never-export" not in decoded_member
        import hashlib
        checksums = json.loads(archive.read("SHA256SUMS.json"))
        assert all(hashlib.sha256(archive.read(name)).hexdigest() == checksum for name, checksum in checksums.items())
    assert not list((repo / ".runtime" / "exports").glob("*.zip"))
    assert client.post("/api/reset").status_code == 200
    assert raw.read_bytes() == original
    assert len(client.get("/api/jobs").json()) == 1
    # A new dashboard process recovers history without altering observations.
    recovered = JobManager(manager.root, repo)
    assert recovered.jobs[job_id]["status"] == "completed"
    assert raw.read_bytes() == original


def test_rejects_host_origin_traversal_and_unfrozen_real_study(console, monkeypatch):
    client, manager, repo = console
    assert client.get("/api/health", headers={"host": "attacker.example"}).status_code == 403
    assert client.post("/api/reset", headers={"origin": "https://attacker.example"}).status_code == 403
    assert client.post("/api/reset", headers={"origin": "http://127.0.0.1:9999"}).status_code == 403
    assert client.post("/api/jobs", json={"conditions": ["C0", "C0"]}).status_code == 422
    assert client.post("/api/jobs", json={"theft_delay_seconds": 0}).status_code == 422
    assert client.post("/api/jobs", json={"theft_delay_seconds": 1801}).status_code == 422
    assert client.post("/api/jobs", json={"phase": "full"}).status_code == 422
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert client.post("/api/jobs", json={"mode": "llm", "model": "test-model", "budget_usd": 1}).status_code == 409
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-not-used")
    assert client.post("/api/jobs", json={"mode": "llm", "phase": "full", "model": "test-model", "budget_usd": 1}).status_code == 409
    monkeypatch.setattr(manager, "_command", lambda *_: 0)
    job_id = client.post("/api/jobs", json={"conditions": ["C0"], "scenarios": ["S1"]}).json()["id"]
    wait_finished(client, job_id)
    outside = repo / "secret.json"
    outside.write_text('{"secret":"private"}')
    response = client.get(f"/api/jobs/{job_id}/trace", params={"path": "../../secret.json"})
    assert response.status_code == 404
    gzip_traversal = client.get(f"/api/jobs/{job_id}/trace", params={"path": "../../secret.jsonl.gz"})
    assert gzip_traversal.status_code == 404
    root = manager.root / job_id
    (root / "arbitrary.gz").write_bytes(gzip.compress(b"not supported evidence"))
    assert client.get(f"/api/jobs/{job_id}/trace", params={"path": "arbitrary.gz"}).status_code == 404
    (root / "oversized.jsonl.gz").write_bytes(gzip.compress(b'{"text":"' + b"a" * 2_000_000 + b'"}\n'))
    assert client.get(f"/api/jobs/{job_id}/trace", params={"path": "oversized.jsonl.gz"}).status_code == 422


def test_single_active_batch_cancel_and_restart_recovery(console, monkeypatch):
    client, manager, repo = console
    import threading
    entered = threading.Event()
    release = threading.Event()

    def command(*_):
        entered.set()
        release.wait(2)
        return 0

    monkeypatch.setattr(manager, "_command", command)
    job_id = client.post("/api/jobs", json={"conditions": ["C0"], "scenarios": ["S1"]}).json()["id"]
    assert entered.wait(1)
    assert client.post("/api/jobs", json={}).status_code == 409
    assert client.post("/api/reset").status_code == 409
    assert client.get(f"/api/jobs/{job_id}/bundle").status_code == 409
    assert client.post(f"/api/jobs/{job_id}/cancel").status_code == 200
    release.set()
    assert wait_finished(client, job_id)["status"] == "cancelled"
    # Simulate a stale record from an abruptly terminated dashboard process.
    with manager.lock:
        manager.jobs[job_id]["status"] = "running"
        manager._save(manager.jobs[job_id])
    recovered = JobManager(manager.root, repo)
    assert recovered.jobs[job_id]["status"] == "interrupted"


def test_provider_specific_readiness_and_svg_plot(console, monkeypatch):
    client, manager, repo = console
    import importlib
    module = importlib.import_module("dashboard.app")
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "engine-ready", ""))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fixture-secret-not-used-for-paid-calls")
    monkeypatch.setenv("STUDY_BUDGET_USD", "4")
    deepseek = client.get("/api/preflight?model=deepseek-flash").json()
    assert deepseek["selected_provider"] == "DeepSeek"
    assert deepseek["required_key_present"] is True
    assert client.get("/api/preflight?model=gpt-test").json()["required_key_present"] is False
    assert "fixture-secret" not in json.dumps(deepseek)

    def command(job, args, log):
        root = manager.root / job["id"]
        (root / "analysis").mkdir(exist_ok=True)
        (root / "analysis" / "outcomes.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"></svg>', encoding="utf-8")
        return 0

    monkeypatch.setattr(manager, "_command", command)
    # The runner fixture makes no network calls; this tests provider selection only.
    job_id = client.post("/api/jobs", json={"mode": "llm", "model": "deepseek-flash", "budget_usd": 1}).json()["id"]
    wait_finished(client, job_id)
    plot = client.get(f"/api/jobs/{job_id}/trace", params={"path": "analysis/outcomes.svg"})
    assert plot.status_code == 200
    assert plot.headers["content-type"] == "image/svg+xml"


def test_cli_batch_discovery_is_read_only_and_tracks_real_completion(console):
    client, manager, repo = console
    folder = manager.root / "pilot-from-cli"
    folder.mkdir()
    manifest_path = folder / "manifest.json"
    manifest_path.write_text(json.dumps({"created_at": 123, "mode": "llm", "phase": "pilot", "pid": 12345}), encoding="utf-8")
    original = manifest_path.read_bytes()
    (folder / "config.json").write_text(json.dumps({"mode": "llm", "phase": "pilot", "conditions": ["C0"], "scenarios": ["S1"]}), encoding="utf-8")
    (folder / "progress.json").write_text('{"completed":1,"total":2,"failures":0}', encoding="utf-8")
    discovered = client.get("/api/jobs").json()
    assert len(discovered) == 1
    assert discovered[0]["external"] is True
    assert discovered[0]["status"] == "running"
    assert discovered[0]["evidence_label"] == "REAL LLM"
    assert discovered[0]["progress"]["total"] == 2
    assert client.post("/api/jobs/pilot-from-cli/cancel").status_code == 409
    assert client.post("/api/jobs", json={}).status_code == 409
    assert client.get("/api/jobs/pilot-from-cli/bundle").status_code == 409
    recovered = JobManager(manager.root, repo)
    assert recovered.jobs["pilot-from-cli"]["status"] == "running"
    assert not (folder / "job.json").exists()
    assert manifest_path.read_bytes() == original
    # Only the harness completion marker changes the observed collection state.
    (folder / "batch-status.json").write_text('{"planned":2,"remaining_failures":0}', encoding="utf-8")
    finished = client.get("/api/jobs/pilot-from-cli").json()
    assert finished["status"] == "completed"
    assert "analysis not generated" in finished["message"]
    assert client.get("/api/jobs/pilot-from-cli/bundle").status_code == 200
    assert client.post("/api/reset").status_code == 200
    assert manifest_path.read_bytes() == original
    assert not (folder / "job.json").exists()
