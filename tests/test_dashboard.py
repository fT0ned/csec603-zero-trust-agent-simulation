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


def test_monitoring_compacts_large_summaries_and_invalidates_cache(console, monkeypatch):
    client, manager, repo = console
    folder = manager.root / "large-cli"
    run = folder / "runs" / "large-run"
    run.mkdir(parents=True)
    (folder / "manifest.json").write_text('{"mode":"llm","phase":"full"}')
    (folder / "config.json").write_text('{"mode":"llm","phase":"full"}')
    summary = run / "summary.json"
    raw = {"status": "completed", "condition": "C2", "scenario": "S4",
           "latencies_ms": [1] * 10000 + [9], "authorization_ms": [2] * 10001,
           "large_unknown": {"events": list(range(10001))},
           "metadata": {"model": "deepseek-flash", "model_snapshot": "returned-model", "approval_dependent": False}}
    summary.write_text(json.dumps(raw))
    original = summary.read_bytes()
    reads = []
    real_read = Path.read_text

    def tracked_read(path, *args, **kwargs):
        if path == summary:
            reads.append(path)
        return real_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", tracked_read)
    assert client.get("/api/jobs").json()[0]["completed_runs"] == 1
    compact = client.get("/api/jobs/large-cli/runs")
    assert len(compact.content) < 1000
    item = compact.json()[0]
    assert item["run_median_latency_ms"] == 1
    assert item["model_snapshot"] == "returned-model"
    assert item["approval_dependent"] is False
    assert "latencies_ms" not in item and "large_unknown" not in item and "authorization_ms" not in item
    for _ in range(3):
        client.get("/api/jobs")
        client.get("/api/jobs/large-cli/runs")
    assert len(reads) == 1
    assert all(not isinstance(value, (dict, list)) for _, cached in manager.summary_cache.values() for value in cached.values())

    # Export and trace routes retain complete arrays; caching never rewrites raw data.
    exported = client.get("/api/jobs/large-cli/export.json").json()[0]
    assert exported["latencies_ms"] == raw["latencies_ms"]
    assert exported["large_unknown"] == raw["large_unknown"]
    assert "latencies_ms" in client.get("/api/jobs/large-cli/export.csv").text
    assert json.loads(client.get("/api/jobs/large-cli/trace", params={"path": "runs/large-run/summary.json"}).text)["authorization_ms"] == raw["authorization_ms"]
    assert summary.read_bytes() == original

    # Same-size rewrites invalidate on nanosecond mtime; size changes invalidate
    # even if a filesystem preserves the previous timestamp.
    import os
    previous = summary.stat()
    raw["latencies_ms"] = [9] * 10000 + [1]
    summary.write_text(json.dumps(raw))
    assert summary.stat().st_size == previous.st_size
    os.utime(summary, ns=(previous.st_atime_ns, previous.st_mtime_ns + 1_000_000))
    assert client.get("/api/jobs/large-cli/runs").json()[0]["run_median_latency_ms"] == 9
    before = len(reads)
    previous = summary.stat()
    with summary.open("a") as stream:
        stream.write(" ")
    os.utime(summary, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    client.get("/api/jobs")
    assert len(reads) == before + 1
    client.get("/api/jobs/large-cli/runs")
    assert len(reads) == before + 1


def test_external_operator_interruption_is_not_reported_as_infrastructure_failure(console):
    client, manager, repo = console
    folder = manager.root / "partial-cli"
    folder.mkdir()
    (folder / "manifest.json").write_text('{"mode":"llm","phase":"full"}')
    (folder / "config.json").write_text('{"mode":"llm","phase":"full"}')
    marker = folder / "batch-status.json"
    marker.write_text(json.dumps({"remaining_failures": 32, "interrupted": True, "reason": "operator monitoring repair; partial collection"}))
    original = marker.read_bytes()
    result = client.get("/api/jobs/partial-cli").json()
    assert result["status"] == "interrupted"
    assert "operator monitoring repair" in result["message"]
    assert "infrastructure failures" not in result["message"]
    assert marker.read_bytes() == original
    assert not (folder / "job.json").exists()


def test_sealed_temporary_checkpoint_is_complete_safe_json_export(console):
    client, manager, repo = console
    import hashlib
    folder = manager.root / "sealed-tmp-cli"
    run = folder / "runs" / "run-1"
    run.mkdir(parents=True)
    (folder / "manifest.json").write_text('{"mode":"llm","phase":"full"}')
    (folder / "config.json").write_text('{"mode":"llm","phase":"full"}')
    (folder / "batch-status.json").write_text('{"remaining_failures":0}')
    checkpoint = run / "checkpoint.json.tmp"
    original = b'\xef\xbb\xbf{"count": 4, "credential": "temporary-disposable-bearer"}\r\n'
    checkpoint.write_bytes(original)
    manifest = run / "raw-manifest.json"
    manifest.write_text(json.dumps({"files": {"checkpoint.json.tmp": hashlib.sha256(original).hexdigest()}}))
    (run / "other.json.tmp").write_text('{"count":4}')
    (folder / "checkpoint.json.tmp").write_bytes(original)
    path = "runs/run-1/checkpoint.json.tmp"
    response = client.get("/api/jobs/sealed-tmp-cli/trace", params={"path": path})
    assert response.status_code == 200
    assert response.json() == {"count": 4, "credential": "[REDACTED]"}
    assert client.get("/api/jobs/sealed-tmp-cli/trace", params={"path":"runs/run-1/other.json.tmp"}).status_code == 404
    assert client.get("/api/jobs/sealed-tmp-cli/trace", params={"path":"checkpoint.json.tmp"}).status_code == 404
    assert client.get("/api/jobs/sealed-tmp-cli/trace", params={"path":"../../checkpoint.json.tmp"}).status_code == 404
    exported = client.get("/api/jobs/sealed-tmp-cli/bundle")
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert json.loads(archive.read("results/" + path)) == response.json()
        assert "results/runs/run-1/other.json.tmp" not in archive.namelist()
        sums = json.loads(archive.read("SHA256SUMS.json"))
        assert hashlib.sha256(archive.read("results/" + path)).hexdigest() == sums["results/" + path]
    assert checkpoint.read_bytes() == original
    checkpoint.write_text('{"count":5}')
    assert client.get("/api/jobs/sealed-tmp-cli/trace", params={"path":path}).status_code == 404
    manifest.write_text('{"files":{}}')
    assert client.get("/api/jobs/sealed-tmp-cli/trace", params={"path":path}).status_code == 404


def test_quality_failure_and_unit_counts_do_not_rewrite_retained_attempts(console):
    client, manager, repo = console
    folder = manager.root / "quality-cli"
    folder.mkdir()
    (folder / "manifest.json").write_text('{"mode":"llm","phase":"full"}')
    (folder / "config.json").write_text('{"mode":"llm","phase":"full"}')
    (folder / "batch-status.json").write_text('{"remaining_failures":0}')
    validation = folder / "validation.json"
    validation.write_text('{"passed":false,"errors":["handoff exceeded tolerance"]}')
    original = validation.read_bytes()
    for run_id, status in [("failed-original","infrastructure_error"),("replacement","completed"),("duplicate","completed")]:
        run = folder / "runs" / run_id
        run.mkdir(parents=True)
        (run / "summary.json").write_text(json.dumps({"condition":"C1","pair_id":"S4-300-now-603","status":status}))
    snapshot = client.get("/api/jobs/quality-cli").json()
    assert snapshot["status"] == "completed"
    assert snapshot["quality"]["status"] == "failed"
    assert snapshot["quality"]["errors"] == ["validation.json: handoff exceeded tolerance"]
    assert snapshot["quality"]["assessments"][0]["passed"] is False
    assert snapshot["completed_runs"] == 1
    assert snapshot["retained_failed_runs"] == 1
    assert snapshot["recorded_attempts"] == 3
    assert len(client.get("/api/jobs/quality-cli/runs").json()) == 3
    assert len(client.get("/api/jobs/quality-cli/export.json").json()) == 3
    assert validation.read_bytes() == original


def test_prompt_profile_and_extension_config_provenance(console):
    from dashboard.app import ExperimentConfig
    from pydantic import ValidationError
    client, manager, repo = console
    config = ExperimentConfig(system_prompt_profile="neutral-v1", protocol_id="extension-v1", study_kind="exploratory-neutral-pilot")
    assert config.system_prompt_profile == "neutral-v1"
    assert ExperimentConfig().system_prompt_profile == "original-v1"
    assert "protocol_id" not in ExperimentConfig().model_dump(exclude_none=True)
    with pytest.raises(ValidationError):
        ExperimentConfig(system_prompt_profile="silent-fallback")
    with pytest.raises(ValidationError):
        ExperimentConfig(protocol_id="../../outside")
    (repo / "configs").mkdir()
    for name in ["neutral-pilot", "enforcement-stress"]:
        (repo / "configs" / (name + ".json")).write_text(config.model_dump_json(exclude_none=True))
        loaded = client.get("/api/configs/" + name)
        assert loaded.status_code == 200
        assert loaded.json()["system_prompt_profile"] == "neutral-v1"
        assert loaded.json()["protocol_id"] == "extension-v1"
    page = client.get("/").text
    assert 'id="system-prompt-profile"' in page
    assert 'id="quality-warning"' in page


def test_clean_gzip_preserves_sealed_bytes_and_redaction_is_explicit(console, monkeypatch):
    import hashlib
    client, manager, repo = console
    secret = "provider-private-value-should-never-export"
    monkeypatch.setenv("DEEPSEEK_API_KEY", secret)
    folder = manager.root / "gzip-sealed-cli"
    run = folder / "runs" / "run-1"
    run.mkdir(parents=True)
    (folder / "manifest.json").write_text('{"mode":"llm","phase":"pilot"}')
    (folder / "config.json").write_text('{"mode":"llm","phase":"pilot"}')
    (folder / "batch-status.json").write_text('{"remaining_failures":0}')
    # More than 2 MB decoded, with each record bounded below the 1 MB limit.
    lines = [json.dumps({"action":"read", "description":"safe" * 20000}, separators=(",", ":")) + "\r\n" for _ in range(30)]
    clean = gzip.compress("".join(lines).encode(), compresslevel=1, mtime=1712345678)
    changed = gzip.compress(("".join(lines) + json.dumps({"api_key":secret}) + "\n").encode(), compresslevel=1, mtime=1712345678)
    (run / "audit.jsonl.gz").write_bytes(clean)
    (run / "actions.jsonl.gz").write_bytes(changed)
    seals = {"audit.jsonl.gz":hashlib.sha256(clean).hexdigest(), "actions.jsonl.gz":hashlib.sha256(changed).hexdigest()}
    raw_manifest = json.dumps({"files":seals},indent=2).encode()
    (run / "raw-manifest.json").write_bytes(raw_manifest)
    exported = client.get("/api/jobs/gzip-sealed-cli/bundle")
    assert exported.status_code == 200
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        clean_name = "results/runs/run-1/audit.jsonl.gz"
        changed_name = "results/runs/run-1/actions.jsonl.gz"
        assert archive.read(clean_name) == clean
        assert hashlib.sha256(archive.read(clean_name)).hexdigest() == seals["audit.jsonl.gz"]
        assert archive.read("results/runs/run-1/raw-manifest.json") == raw_manifest
        redacted = gzip.decompress(archive.read(changed_name))
        assert secret.encode() not in redacted
        assert json.loads(redacted.splitlines()[-1]) == {"api_key":"[REDACTED]"}
        assert archive.read(changed_name) != changed
        provenance = json.loads(archive.read("EXPORT_PROVENANCE.json"))
        assert clean_name not in provenance["altered_files"]
        assert provenance["altered_sealed_members"] == [changed_name]
        assert provenance["missing_sealed_members"] == []
        assert provenance["original_raw_manifests_preserved"] is True
        assert "CANNOT validate" in provenance["warning"]
        assert "NOT PERFORMED" in provenance["raw_seal_validation"]
        entry = provenance["altered_files"][changed_name]
        assert entry["original_sha256"] == seals["actions.jsonl.gz"]
        assert entry["exported_sha256"] == hashlib.sha256(archive.read(changed_name)).hexdigest()
        sums = json.loads(archive.read("SHA256SUMS.json"))
        assert sums["EXPORT_PROVENANCE.json"] == hashlib.sha256(archive.read("EXPORT_PROVENANCE.json")).hexdigest()
    assert (run / "audit.jsonl.gz").read_bytes() == clean
    assert (run / "actions.jsonl.gz").read_bytes() == changed
    assert (run / "raw-manifest.json").read_bytes() == raw_manifest


def test_prepared_repair_protocol_is_inactive_and_preserved(console, monkeypatch):
    client, manager, repo = console
    folder = manager.root / "prepared-repair"
    folder.mkdir()
    for name, value in {"manifest.json":{"mode":"llm","phase":"full"}, "config.json":{"mode":"llm","phase":"full"}, "repair-protocol.json":{"prepared":True}}.items():
        (folder/name).write_text(json.dumps(value))
    original = {p.name:p.read_bytes() for p in folder.iterdir()}
    job = client.get("/api/jobs/prepared-repair").json()
    assert job["status"] == "prepared"
    assert job["message"] == "Protocol prepared; no trials started"
    assert job["completed_runs"] == 0
    assert client.post("/api/reset").status_code == 200
    monkeypatch.setattr(manager, "_command", lambda *_:0)
    started = client.post("/api/jobs", json={"conditions":["C0"],"scenarios":["S1"]})
    assert started.status_code == 202
    wait_finished(client, started.json()["id"])
    assert {p.name:p.read_bytes() for p in folder.iterdir()} == original
    (folder / "started.json").write_text('{"started":true}')
    assert client.get("/api/jobs/prepared-repair").json()["status"] == "running"
    (folder / "started.json").unlink()
    (folder / "runs").mkdir()
    assert client.get("/api/jobs/prepared-repair").json()["status"] == "running"


def test_generated_pdf_and_all_figure_manifest_members_preserve_bytes(console):
    import hashlib
    client, manager, repo = console
    folder = manager.root / "paper-figures-cli"
    figures = folder / "figures"
    figures.mkdir(parents=True)
    (folder / "manifest.json").write_text('{"mode":"llm","phase":"pilot"}')
    (folder / "config.json").write_text('{"mode":"llm","phase":"pilot"}')
    (folder / "batch-status.json").write_text('{"remaining_failures":0}')
    # Binary bytes that cannot survive UTF-8 decode; >1 MB exercises streaming.
    pdf = b"%PDF-1.7\n%" + bytes(range(256)) * 5000 + b"\n%%EOF\n"
    contents = {"rates.pdf":pdf, "rates.png":b"\x89PNG\r\n\x1a\n\xff\xfe", "rates.svg":b'<svg xmlns="http://www.w3.org/2000/svg"/>', "endpoint-rates.csv":b"condition,n\nC2,4\n", "descriptive-run-metrics.csv":b"condition,median\nC2,2.0\n", "cohort-labels.csv":b"mode,phase\nllm,pilot\n", "README.md":b"Generated figures.\n"}
    exports = {}
    for name, content in contents.items():
        (figures/name).write_bytes(content)
        exports[name] = hashlib.sha256(content).hexdigest()
    figure_manifest = json.dumps({"kind":"postcollection", "exports":exports},indent=2).encode()
    (figures / "figure-manifest.json").write_bytes(figure_manifest)
    (folder / "unscoped.pdf").write_bytes(pdf)
    (figures / "unlisted.pdf").write_bytes(pdf)
    response = client.get("/api/jobs/paper-figures-cli/trace",params={"path":"figures/rates.pdf"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == pdf
    listed = {item["path"] for item in client.get("/api/jobs/paper-figures-cli/files?include_runs=false").json()}
    assert "figures/rates.pdf" in listed and "figures/unlisted.pdf" not in listed
    assert client.get("/api/jobs/paper-figures-cli/trace",params={"path":"unscoped.pdf"}).status_code == 404
    exported = client.get("/api/jobs/paper-figures-cli/bundle")
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        sealed = json.loads(archive.read("results/figures/figure-manifest.json"))["exports"]
        sums = json.loads(archive.read("SHA256SUMS.json"))
        for name, expected in sealed.items():
            member = "results/figures/" + name
            assert archive.read(member) == contents[name]
            assert hashlib.sha256(archive.read(member)).hexdigest() == expected == sums[member]
        provenance = json.loads(archive.read("EXPORT_PROVENANCE.json"))
        assert "results/figures/rates.pdf" not in provenance["altered_files"]
    assert (figures / "rates.pdf").read_bytes() == pdf
    assert (figures / "figure-manifest.json").read_bytes() == figure_manifest
    (figures / "rates.pdf").write_bytes(pdf + b"changed")
    assert client.get("/api/jobs/paper-figures-cli/trace",params={"path":"figures/rates.pdf"}).status_code == 404


def test_additive_semantic_veto_overrides_passing_collector_checks(console):
    client, manager, repo = console
    folder = manager.root / "repair-quality"
    run = folder / "runs" / "trial"
    run.mkdir(parents=True)
    for name,value in {"manifest.json":{"mode":"llm","phase":"full"}, "config.json":{"mode":"llm","phase":"full"}, "batch-status.json":{"remaining_failures":0}, "quality.json":{"passed":True,"scope":"clock checks only","errors":[]}, "validation.json":{"passed":True,"errors":[]}}.items():
        (folder/name).write_text(json.dumps(value))
    (run / "summary.json").write_text('{"status":"completed","condition":"C0","scenario":"S4"}')
    original = {p.relative_to(folder).as_posix():p.read_bytes() for p in folder.rglob('*') if p.is_file()}
    assert client.get('/api/jobs/repair-quality').json()['quality']['status'] == 'passed'
    adjudication = folder / "quality-adjudication.json"
    adjudication.write_text(json.dumps({"passed":False,"scope":"terminal event semantics","errors":["Allowed=true tool error is not credential denial"]}))
    quality = client.get('/api/jobs/repair-quality').json()['quality']
    assert quality['status'] == 'failed'
    assert any('quality-adjudication.json' in e and 'not credential denial' in e for e in quality['errors'])
    assert len(quality['assessments']) == 3
    assert client.get('/api/jobs/repair-quality/export.json').json()[0]['_batch_quality_status'] == 'failed'
    assert '_batch_quality_status' in client.get('/api/jobs/repair-quality/export.csv').text
    with zipfile.ZipFile(io.BytesIO(client.get('/api/jobs/repair-quality/bundle').content)) as archive:
        provenance = json.loads(archive.read('EXPORT_PROVENANCE.json'))
        assert provenance['batch_quality']['status'] == 'failed'
        assert json.loads(archive.read('results/quality.json'))['passed'] is True
        assert json.loads(archive.read('results/quality-adjudication.json'))['passed'] is False
    assert all((folder/name).read_bytes() == content for name,content in original.items())


def test_sibling_quality_review_requires_exact_collection_and_path_binding(console):
    client, manager, repo = console
    folder = manager.root / "study-original"
    folder.mkdir()
    (folder / 'manifest.json').write_text('{"mode":"llm","phase":"full"}')
    (folder / 'config.json').write_text('{"mode":"llm","phase":"full"}')
    (folder / 'batch-status.json').write_text('{"remaining_failures":0}')
    validation = folder / 'validation.json'
    validation.write_text('{"passed":true,"scope":"original checks"}')
    original = validation.read_bytes()
    review_dir = manager.root / 'quality-review'
    review_dir.mkdir()
    review = review_dir / 'quality-adjudication.json'
    record = {'collection_id':'study-original','collection_path':'results/study-original','passed':False,'scope':'external semantic adjudication','errors':['Tool failure was misclassified as denial']}
    review.write_text(json.dumps(record))
    preserved = review.read_bytes()
    quality = client.get('/api/jobs/study-original').json()['quality']
    assert quality['status'] == 'failed'
    assert quality['assessments'][1]['path'] == 'external-quality/quality-review/quality-adjudication.json'
    with zipfile.ZipFile(io.BytesIO(client.get('/api/jobs/study-original/bundle').content)) as archive:
        assert archive.read('results/external-quality/quality-review/quality-adjudication.json') == preserved
        assert json.loads(archive.read('EXPORT_PROVENANCE.json'))['batch_quality']['status'] == 'failed'
    assert validation.read_bytes() == original and review.read_bytes() == preserved
    record['collection_id'] = 'different-study'
    review.write_text(json.dumps(record))
    assert client.get('/api/jobs/study-original').json()['quality']['status'] == 'passed'
    record['collection_id'] = 'study-original'
    record['collection_path'] = 'results/different-study'
    review.write_text(json.dumps(record))
    rejected = client.get('/api/jobs/study-original').json()['quality']
    assert rejected['status'] == 'unreadable'
    assert any('does not bind' in e for e in rejected['errors'])
    with zipfile.ZipFile(io.BytesIO(client.get('/api/jobs/study-original/bundle').content)) as archive:
        assert 'results/external-quality/quality-review/quality-adjudication.json' not in archive.namelist()
    record['collection_path'] = 'results/../results/study-original'
    review.write_text(json.dumps(record))
    assert client.get('/api/jobs/study-original').json()['quality']['status'] == 'unreadable'
    assert validation.read_bytes() == original
