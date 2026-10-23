"""Loopback-only dashboard. Raw observations are never modified by this service."""
from __future__ import annotations

import csv
from contextlib import asynccontextmanager
import codecs
import hashlib
import gzip
import io
import json
import math
import statistics
import os
from pathlib import Path
import re
import signal
import tempfile
import subprocess
import sys
import threading
import time
from typing import Literal
from urllib.parse import urlparse
import uuid
import zipfile

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.background import BackgroundTask

REPO = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).parent / "static"
ALLOWED_SUFFIXES = {".pdf", ".json", ".jsonl", ".gz", ".csv", ".svg", ".png", ".jpg", ".jpeg", ".md", ".mmd", ".txt", ".log", ".rego", ".yaml", ".yml", ".toml", ".py", ".html", ".css", ".js", ".ps1", ".sh", ".conf"}
TERMINAL = {"completed", "failed", "cancelled", "interrupted", "prepared"}


def load_local_env(repo: Path):
    """Read simple local env assignments without executing shell expressions."""
    path = repo / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
                value = value.strip()
                if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                os.environ.setdefault(key, value)


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["scripted", "llm"] = "scripted"
    phase: Literal["engineering", "pilot", "full"] = "engineering"
    system_prompt_profile: Literal["original-v1", "neutral-v1"] = "original-v1"
    protocol_id: str | None = Field(default=None, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    study_kind: str | None = Field(default=None, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    conditions: list[Literal["C0", "C1", "C2", "C2-noWF", "C2-RS"]] = ["C0", "C1", "C2"]
    scenarios: list[Literal["S1", "S2", "S3", "S4", "S5"]] = ["S1", "S2", "S5"]
    repeats: int = Field(default=1, ge=1, le=300)
    ttl_seconds: list[int] = [900]
    revocation_modes: list[Literal["now", "expiry"]] = ["now", "expiry"]
    seed: int = Field(default=603, ge=0, le=2147483647)
    probe_interval_seconds: float = Field(default=0.1, ge=0.05, le=60)
    s3_probe_interval_seconds: float = Field(default=10.0, ge=0.05, le=60)
    observation_seconds: float = Field(default=2.0, ge=0.1, le=7200)
    observation_margin_seconds: int = Field(default=5, ge=5, le=180)
    theft_delay_seconds: int = Field(default=120, ge=1, le=1800)
    concurrency: int = Field(default=1, ge=1, le=32)
    model: str = Field(default="deepseek-flash", max_length=150, pattern=r"^[A-Za-z0-9_.:/-]*$")
    budget_usd: float = Field(default=4, ge=0, le=10000)

    @model_validator(mode="after")
    def consistent(self):
        for name in ("conditions", "scenarios", "ttl_seconds", "revocation_modes"):
            items = getattr(self, name)
            if not items or len(set(items)) != len(items):
                raise ValueError(f"{name} must be nonempty and unique")
        if any(t not in (300, 900, 3600) for t in self.ttl_seconds):
            raise ValueError("Credential lifetimes must be 300, 900, or 3600 seconds")
        if self.mode == "llm" and (not self.model or self.budget_usd <= 0):
            raise ValueError("Real LLM runs require a model and positive explicit budget")
        if self.phase == "full" and self.mode != "llm":
            raise ValueError("Full research experiments require real LLM mode")
        if not set(self.conditions) & {"C0", "C1", "C2"} and not set(self.scenarios) & {"S2", "S5"}:
            raise ValueError("Cut-down conditions apply only to S2 and S5")
        return self


SECRET_ENV_PATTERN = re.compile(r"API_KEY|SECRET|TOKEN|PASSWORD", re.I)
SECRET_FIELD_PATTERN = re.compile(r"(^|_)(api_key|secret|password|authorization|access_token|jwt|credential|token)$", re.I)
API_KEY_PATTERN = re.compile(r"\bsk-[A-Za-z0-9_-]{12,}")
JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")


def redact(value, secret_values=None):
    """Sanitize exports, never the preserved evidence source."""
    if secret_values is None:
        secret_values = tuple(secret for key, secret in os.environ.items() if SECRET_ENV_PATTERN.search(key) and len(secret) >= 12)
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if SECRET_FIELD_PATTERN.search(k) else redact(v, secret_values)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, secret_values) for v in value]
    if not isinstance(value, str):
        return value
    for secret in secret_values:
        value = value.replace(secret, "[REDACTED]")
    value = API_KEY_PATTERN.sub("[REDACTED_API_KEY]", value)
    value = JWT_PATTERN.sub("[REDACTED_JWT]", value)
    return value


def sealed_checkpoint(root: Path, candidate: Path) -> bool:
    """Permit only the known JSON checkpoint sealed in this run's raw manifest."""
    parts = candidate.relative_to(root.resolve()).parts
    if len(parts) != 3 or parts[0] != "runs" or parts[2] != "checkpoint.json.tmp" or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", parts[1]):
        return False
    try:
        manifest = (candidate.parent / "raw-manifest.json").resolve()
        if not manifest.is_relative_to(root.resolve()) or candidate.stat().st_size > 1024 * 1024 or manifest.stat().st_size > 1024 * 1024:
            return False
        expected = json.loads(manifest.read_text(encoding="utf-8"))["files"].get(candidate.name)
        content = candidate.read_bytes()
        return isinstance(expected, str) and hashlib.sha256(content).hexdigest() == expected and isinstance(json.loads(content), dict)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def generated_pdf(root: Path, candidate: Path) -> bool:
    """Allow only generated figures whose bytes match their local figure manifest."""
    parts = candidate.relative_to(root.resolve()).parts
    if len(parts) != 2 or parts[0] != "figures" or candidate.suffix != ".pdf":
        return False
    try:
        manifest = (candidate.parent / "figure-manifest.json").resolve()
        if not manifest.is_relative_to(root.resolve()) or manifest.stat().st_size > 1024 * 1024:
            return False
        expected = json.loads(manifest.read_text(encoding="utf-8"))["exports"].get(candidate.name)
        with candidate.open("rb") as stream:
            if stream.read(5) != b"%PDF-":
                return False
            stream.seek(0)
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        return isinstance(expected, str) and actual == expected
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def safe_file(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
        raise HTTPException(404, "File not found")
    if (candidate.suffix not in ALLOWED_SUFFIXES and candidate.name != "Dockerfile" and not sealed_checkpoint(root, candidate)) or any(x.startswith(".") for x in candidate.relative_to(root.resolve()).parts):
        raise HTTPException(404, "File not exportable")
    if candidate.suffix == ".pdf" and not generated_pdf(root, candidate):
        raise HTTPException(404, "Only manifest-bound generated PDF figures are exportable")
    if candidate.suffix == ".gz" and not candidate.name.endswith(".jsonl.gz"):
        raise HTTPException(404, "Only compressed JSONL evidence is exportable")
    return candidate


def sanitized_bytes(path: Path) -> bytes:
    if path.suffix in {".png", ".jpg", ".jpeg", ".pdf"}:
        return path.read_bytes()
    content = path.read_bytes().decode("utf-8", errors="replace")
    try:
        if path.suffix == ".json" or path.name == "checkpoint.json.tmp":
            original = json.loads(content.lstrip("\ufeff"))
            sanitized = redact(original)
            if sanitized == original:
                return content.encode("utf-8")
            return json.dumps(sanitized, indent=2, ensure_ascii=False).encode()
        if path.suffix == ".jsonl":
            original = [json.loads(line) for line in content.splitlines() if line.strip()]
            sanitized = redact(original)
            if sanitized == original:
                return content.encode("utf-8")
            return ("\n".join(json.dumps(line, ensure_ascii=False) for line in sanitized) + "\n").encode()
    except (ValueError, TypeError):
        pass
    return redact(content).encode("utf-8")


def redact_large_text(content, suffix):
    content = redact(content)
    if suffix in {".json", ".jsonl", ".log"}:
        content = re.sub(r'("(?:api_key|secret|password|authorization|access_token|jwt|credential|token)"\s*:\s*)"(?:\\.|[^"\\])*"', r'\1"[REDACTED]"', content, flags=re.I)
    return content


def sanitized_chunks(path: Path, secret_values=None):
    """Bound export memory; structured traces rotate at 1 MB in the harness."""
    chunk_size = 1024 * 1024
    if secret_values is None:
        secret_values = tuple(secret for key, secret in os.environ.items() if SECRET_ENV_PATTERN.search(key) and len(secret) >= 12)
    if path.name.endswith(".jsonl.gz"):
        with gzip.open(path, "rb") as stream:
            while line := stream.readline(chunk_size + 1):
                if len(line) > chunk_size:
                    raise ValueError("Compressed evidence record exceeds the 1 MB export limit")
                if line.strip():
                    yield (json.dumps(redact(json.loads(line), secret_values), ensure_ascii=False) + "\n").encode("utf-8")
        return
    if path.stat().st_size <= chunk_size:
        yield sanitized_bytes(path)
        return
    if path.suffix in {".png", ".jpg", ".jpeg", ".pdf"}:
        with path.open("rb") as stream:
            while data := stream.read(chunk_size):
                yield data
        return
    # Keep an overlap so an API key/JWT split across a chunk boundary is redacted.
    # The staged raw traces stay unchanged; only the exported stream is sanitized.
    overlap = max([65536] + [len(value) + 4096 for key, value in os.environ.items() if re.search(r"API_KEY|SECRET|TOKEN|PASSWORD", key, re.I)])
    pending = ""
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    with path.open("rb") as stream:
        while data := stream.read(chunk_size):
            pending += decoder.decode(data)
            pending = redact_large_text(pending, path.suffix)
            if len(pending) > overlap * 2:
                split = len(pending) - overlap
                # Prefer a newline boundary for line-oriented raw records.
                boundary = pending.rfind("\n", 0, split)
                if boundary > 0:
                    split = boundary + 1
                piece, pending = pending[:split], pending[split:]
                yield piece.encode("utf-8")
        pending += decoder.decode(b"", final=True)
        yield redact_large_text(pending, path.suffix).encode("utf-8")


def gzip_needs_redaction(path: Path, secret_values) -> bool:
    """Inspect every decoded record with bounded memory before copying raw gzip."""
    changed = False
    with gzip.open(path, "rb") as stream:
        while line := stream.readline(1024 * 1024 + 1):
            if len(line) > 1024 * 1024:
                raise ValueError("Compressed evidence record exceeds the 1 MB export limit")
            if line.strip():
                original = json.loads(line)
                if redact(original, secret_values) != original:
                    changed = True
    return changed


def zip_sanitized(archive, path: Path, name: str):
    checksum = hashlib.sha256()
    with path.open("rb") as raw:
        raw_checksum = hashlib.file_digest(raw, "sha256").hexdigest()
    secret_values = tuple(secret for key, secret in os.environ.items() if SECRET_ENV_PATTERN.search(key) and len(secret) >= 12)
    compressed_trace = path.name.endswith(".jsonl.gz")
    changed = gzip_needs_redaction(path, secret_values) if compressed_trace else False
    with archive.open(name, "w", force_zip64=True) as member:
        if compressed_trace and not changed:
            # gzip headers, compression settings, whitespace, and raw seals survive.
            with path.open("rb") as raw:
                while content := raw.read(1024 * 1024):
                    member.write(content)
                    checksum.update(content)
        elif compressed_trace:
            class HashingWriter:
                def write(self, content):
                    checksum.update(content)
                    return member.write(content)

                def flush(self):
                    pass

            with gzip.GzipFile(fileobj=HashingWriter(), mode="wb", filename="", mtime=0) as compressed:
                for content in sanitized_chunks(path, secret_values):
                    compressed.write(content)
        else:
            for content in sanitized_chunks(path, secret_values):
                member.write(content)
                checksum.update(content)
    return checksum.hexdigest(), raw_checksum


class JobManager:
    def __init__(self, root: Path, repo: Path = REPO):
        self.root = root.resolve()
        self.repo = repo.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.processes: dict[str, subprocess.Popen] = {}
        self.jobs = {}
        # UI projections only: never retain raw latency/action arrays in memory.
        self.summary_cache = {}
        for path in self.root.glob("*/job.json"):
            try:
                if not path.resolve().is_relative_to(self.root):
                    continue
                job = json.loads(path.read_text(encoding="utf-8"))
                job["id"] = path.parent.name
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", job["id"]) or not isinstance(job.get("config"), dict) or not isinstance(job.get("created_at"), (int, float)):
                    continue
                if job["status"] not in TERMINAL:
                    job.update(status="interrupted", message="Dashboard restarted; preserved partial data. Review before rerunning.", ended_at=time.time())
                self.jobs[path.parent.name] = job
                self._save(job)
            except (ValueError, KeyError, OSError):
                continue
        self.discover_external()

    def _external(self, folder):
        """Observe CLI metadata without rewriting its manifest, progress, or data."""
        if not folder.resolve().is_relative_to(self.root) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", folder.name):
            return
        existing = self.jobs.get(folder.name)
        if existing and not existing.get("external", False):
            return
        try:
            manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
            config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
            if not isinstance(manifest, dict) or not isinstance(config, dict):
                return
            config = {"mode": manifest.get("mode", "unknown"), "phase": manifest.get("phase", "unknown"), "conditions": [], "scenarios": [], **config}
            status = "running"
            message = "Launched from CLI; collection completion marker pending"
            final_path = folder / "batch-status.json"
            analysis = (folder / "analysis" / "report.json").is_file()
            if final_path.is_file():
                final = json.loads(final_path.read_text(encoding="utf-8"))
                remaining = final.get("remaining_failures")
                if final.get("interrupted") is True:
                    status = "interrupted"
                    reason = final.get("reason")
                    message = "CLI collection interrupted; partial evidence retained"
                    if isinstance(reason, str) and reason.strip():
                        message += ": " + reason
                elif isinstance(remaining, int):
                    status = "completed" if remaining == 0 else "failed"
                    message = "CLI collection complete" if remaining == 0 else "CLI collection ended with infrastructure failures; evidence retained"
                    message += "; analysis available" if analysis else "; analysis not generated"
                else:
                    status = "unknown"
                    message = "CLI completion metadata is incomplete; inspect batch-status.json"
            if (folder / "repair-protocol.json").is_file() and not (folder / "started.json").exists() and not (folder / "runs").exists():
                status = "prepared"
                message = "Protocol prepared; no trials started"
            created = manifest.get("created_at")
            if not isinstance(created, (int, float)):
                created = (folder / "manifest.json").stat().st_mtime
            self.jobs[folder.name] = {"id": folder.name, "status": status, "created_at": created, "config": config, "external": True, "managed": False, "message": message, "process_id": manifest.get("pid", manifest.get("process_id")), "analysis_available": analysis}
        except (OSError, ValueError, TypeError):
            return

    def discover_external(self):
        with self.lock:
            for manifest in self.root.glob("*/manifest.json"):
                self._external(manifest.parent)

    def _save(self, job):
        if job.get("external"):
            return
        path = self.root / job["id"] / "job.json"
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(job, indent=2), encoding="utf-8")
        temp.replace(path)

    def get(self, job_id):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", job_id):
            raise HTTPException(404, "Batch not found")
        if job_id not in self.jobs or self.jobs[job_id].get("external"):
            with self.lock:
                self._external(self.root / job_id)
        if job_id not in self.jobs:
            raise HTTPException(404, "Batch not found")
        return self.jobs[job_id]

    def path(self, job_id):
        self.get(job_id)
        return self.root / job_id

    def compact_summary(self, root: Path, path: Path):
        """Cache a bounded UI projection until the raw file's mtime/size changes."""
        resolved = safe_file(root, path.relative_to(root).as_posix())
        with self.lock:
            stat = resolved.stat()
            fingerprint = (stat.st_mtime_ns, stat.st_size)
            cached = self.summary_cache.get(resolved)
            if cached and cached[0] == fingerprint:
                return dict(cached[1])
            raw = json.loads(resolved.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("Summary must be an object")
            fields = ("run_id", "condition", "scenario", "status", "mode", "phase", "collection_id", "seed", "pair_id",
                      "ttl_seconds", "revocation_mode", "unauthorized_outcome", "harmful_attempts",
                      "harmful_executed", "attribution_true", "attribution_predicted")
            item = {key: raw[key] for key in fields if key in raw and isinstance(raw[key], (str, int, float, bool, type(None)))}
            metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
            for key in ("model", "model_snapshot", "approval_dependent", "system_prompt_profile", "protocol_id", "study_kind"):
                value = raw.get(key, metadata.get(key))
                if isinstance(value, (str, int, float, bool, type(None))):
                    item[key] = value
            values = raw.get("latencies_ms")
            if not isinstance(values, list):
                values = [values]
            values = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)]
            item["run_median_latency_ms"] = statistics.median(values) if values else None
            item.setdefault("run_id", path.parent.name)
            item["summary_path"] = path.relative_to(root).as_posix()
            item = redact(item)
            # A writer replacing the summary during this read must invalidate it.
            after = resolved.stat()
            if (after.st_mtime_ns, after.st_size) == fingerprint:
                self.summary_cache[resolved] = (fingerprint, item)
            return dict(item)

    def compact_runs(self, job_id):
        root = self.root / job_id
        result = []
        for path in sorted((root / "runs").glob("*/summary.json")):
            try:
                result.append(self.compact_summary(root, path))
            except (ValueError, OSError, HTTPException):
                continue
        return result

    def quality(self, job_id):
        """Aggregate additive reviews; no passing collector check overrides a veto."""
        root = self.root / job_id
        assessments = []
        sources = [(root / name, name, False) for name in ("validation.json", "quality.json", "quality-adjudication.json") if (root / name).is_file()]
        for review in self.root.glob("*/quality-adjudication.json"):
            if review.parent == root or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", review.parent.name):
                continue
            try:
                resolved = safe_file(self.root, review.relative_to(self.root).as_posix())
                if resolved.stat().st_size > 1024 * 1024:
                    continue
                record = json.loads(resolved.read_text(encoding="utf-8"))
                if isinstance(record, dict) and record.get("collection_id") == job_id:
                    sources.append((resolved, "external-quality/" + review.parent.name + "/quality-adjudication.json", True))
            except (OSError, ValueError, HTTPException):
                continue
        for path, display, external in sources:
            assessment = {"path": display, "status": "unreadable", "scope": "", "errors": []}
            try:
                if not path.resolve().is_relative_to(self.root) or path.stat().st_size > 1024 * 1024:
                    raise ValueError("Assessment is outside results or exceeds 1 MB")
                content = path.read_bytes()
                record = json.loads(content)
                if not isinstance(record, dict):
                    raise ValueError("Quality assessment must be an object")
                if external:
                    declared = record.get("collection_path")
                    if not isinstance(declared, str) or Path(declared).is_absolute() or ".." in Path(declared).parts or (self.repo / declared).resolve() != root.resolve():
                        raise ValueError("External assessment collection_path does not bind this collection")
                passed = record.get("passed")
                assessment.update(status="passed" if passed is True else "failed" if passed is False else "unknown",
                                  passed=passed if isinstance(passed, bool) else None,
                                  scope=record.get("scope") if isinstance(record.get("scope"), str) else "",
                                  source_sha256=hashlib.sha256(content).hexdigest())
                errors = record.get("errors", [])
                assessment["errors"] = [str(error) for error in errors] if isinstance(errors, list) else [str(errors)]
                if assessment["status"] == "failed" and not assessment["errors"]:
                    assessment["errors"] = [str(record.get("reason", "Quality assessment failed"))]
            except (OSError, ValueError, TypeError) as error:
                assessment["errors"] = [str(error)]
            assessments.append(assessment)
        statuses = {item["status"] for item in assessments}
        status = next((candidate for candidate in ("failed", "unreadable", "unknown", "passed") if candidate in statuses), "not_validated")
        errors = [item["path"] + ": " + error for item in assessments if item["status"] != "passed" for error in item["errors"]]
        return redact({"status": status, "errors": errors, "assessments": assessments})

    def snapshot(self, job):
        result = dict(job)
        root = self.root / job["id"]
        rows = self.compact_runs(job["id"])
        completed = [item for item in rows if item.get("status") in (None, "completed")]
        def unit_key(item):
            if item.get("pair_id"):
                return (item.get("condition"), item["pair_id"])
            if item.get("seed") is not None:
                return tuple(item.get(key) for key in ("condition", "scenario", "ttl_seconds", "revocation_mode", "seed"))
            return (item["run_id"],)
        result["completed_runs"] = len({unit_key(item) for item in completed})
        result["retained_failed_runs"] = sum(item.get("status") not in (None, "completed", "running", "pending", "queued") for item in rows)
        result["recorded_attempts"] = len(rows)
        result["quality"] = self.quality(job["id"])
        result["evidence_label"] = {"llm": "REAL LLM", "scripted": "SCRIPTED CONTROL CHECK"}.get(job["config"].get("mode"), "MODE NOT RECORDED")
        status_file = root / "progress.json"
        if status_file.exists():
            try:
                result["progress"] = redact(json.loads(status_file.read_text(encoding="utf-8")))
            except (ValueError, OSError):
                pass
        return redact(result)

    def start(self, config):
        with self.lock:
            self.discover_external()
            if any(job["status"] not in TERMINAL for job in self.jobs.values()):
                raise HTTPException(409, "An experiment is already running. Cancel it before starting another.")
            job_id = time.strftime("%Y%m%dT%H%M%S", time.gmtime()) + "-" + uuid.uuid4().hex[:8]
            path = self.root / job_id
            path.mkdir()
            (path / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
            job = {"id": job_id, "status": "queued", "created_at": time.time(), "config": config, "managed": True, "external": False, "message": "Preparing experiment"}
            self.jobs[job_id] = job
            self._save(job)
            threading.Thread(target=self._run, args=(job,), daemon=True).start()
            return self.snapshot(job)

    def _command(self, job, command, log):
        with self.lock:
            if job["status"] in {"cancelled", "interrupted"}:
                return -1
            flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
            proc = subprocess.Popen(command, cwd=self.repo, stdout=log, stderr=subprocess.STDOUT, creationflags=flags, start_new_session=os.name != "nt", env={**os.environ, "PYTHONUNBUFFERED": "1"})
            self.processes[job["id"]] = proc
        code = proc.wait()
        with self.lock:
            self.processes.pop(job["id"], None)
        return code

    def _run(self, job):
        path = self.root / job["id"]
        try:
            with self.lock:
                if job["status"] in {"cancelled", "interrupted"}:
                    return
                job.update(status="running", started_at=time.time(), message="Collecting observations")
                self._save(job)
            with (path / "runner.log").open("ab") as log:
                code = self._command(job, [sys.executable, "-m", "testbed.cli", "run", "--config", str(path / "config.json"), "--output", str(path)], log)
                if code == 0 and job["status"] not in {"cancelled", "interrupted"}:
                    with self.lock:
                        job.update(status="analyzing", message="Generating reproducible analysis")
                        self._save(job)
                    analysis_code = self._command(job, [sys.executable, "-m", "analysis.cli", "--input", str(path), "--output", str(path / "analysis")], log)
                    job["analysis_exit_code"] = analysis_code
                with self.lock:
                    if job["status"] not in {"cancelled", "interrupted"}:
                        ok = code == 0 and job.get("analysis_exit_code") == 0
                        job.update(status="completed" if ok else "failed", message="Collection and analysis complete" if ok else "Collection or analysis failed; inspect runner.log. Partial evidence retained.")
                    job.update(exit_code=code, ended_at=time.time())
                    self._save(job)
        except Exception as error:
            with self.lock:
                job.update(status="failed", message=redact(str(error)), ended_at=time.time())
                self._save(job)

    def cancel(self, job_id):
        with self.lock:
            job = self.get(job_id)
            if job.get("external"):
                raise HTTPException(409, "This batch was launched from the CLI. Stop it in its original terminal; the dashboard observes it read-only and preserves all evidence.")
            if job["status"] in TERMINAL:
                raise HTTPException(409, "Experiment has already ended")
            job.update(status="cancelled", message="Cancelled; partial raw evidence retained", ended_at=time.time())
            self._save(job)
            proc = self.processes.get(job_id)
            if proc and proc.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    os.killpg(proc.pid, signal.SIGTERM)
            return self.snapshot(job)


def create_app(results_root: Path | None = None, repo: Path = REPO):
    load_local_env(repo)
    manager = JobManager(results_root or Path(os.getenv("TESTBED_RESULTS_DIR", repo / "results")), repo)

    @asynccontextmanager
    async def lifespan(_app):
        yield
        with manager.lock:
            active = [job["id"] for job in manager.jobs.values() if job["status"] not in TERMINAL and not job.get("external")]
        for job_id in active:
            manager.cancel(job_id)
            with manager.lock:
                manager.jobs[job_id].update(status="interrupted", message="Dashboard shut down; runner stopped and partial evidence retained")
                manager._save(manager.jobs[job_id])

    app = FastAPI(title="Leopard Research Console", docs_url=None, redoc_url=None, lifespan=lifespan)
    app.state.manager = manager

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        host = urlparse("http://" + request.headers.get("host", "")).hostname
        if host not in {"localhost", "127.0.0.1", "::1"}:
            return Response("Dashboard accepts loopback hosts only", 403)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            if origin and (urlparse(origin).netloc != request.headers.get("host") or urlparse(origin).scheme not in {"http", "https"}):
                return Response("Cross-origin mutation rejected", 403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'"
        return response

    @app.get("/", response_class=HTMLResponse)
    def home():
        return (STATIC / "index.html").read_text(encoding="utf-8")

    @app.get("/api/docs", response_class=HTMLResponse)
    def api_docs():
        return """<!doctype html><html lang="en"><meta charset="utf-8"><title>Leopard dashboard API</title>
        <h1>Leopard dashboard API</h1><p>Local, loopback-only experiment orchestration. See the <a href="/openapi.json">OpenAPI JSON schema</a> for request and response definitions.</p>
        <ul><li>GET /api/health and /api/preflight: console and prerequisite checks</li>
        <li>GET /api/jobs: preserved collection batches</li><li>POST /api/jobs: validated experiment configuration</li>
        <li>GET /api/jobs/{id}: status and collection progress</li><li>POST /api/jobs/{id}/cancel: cancel collection and preserve partial evidence</li>
        <li>POST /api/reset: reset the console without deleting results</li>
        <li>GET /api/jobs/{id}/runs and /files: summaries and exportable artifacts</li>
        <li>GET /api/jobs/{id}/trace?path=runner.log: sanitized trace</li>
        <li>GET /api/jobs/{id}/export.csv, /export.json, and /bundle: sanitized exports</li></ul>
        <p>Mutation requests from a browser must have the same Origin as this console. Full studies require the approved pre-run freeze and paid runs require credentials and a positive established budget.</p>
        <p><a href="/">Return to the research console</a></p></html>"""

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "dashboard", "results_root": str(manager.root), "raw_data_policy": "Preserved; reset never deletes results"}

    @app.get("/api/preflight")
    def preflight(model: str = "deepseek-flash"):
        load_local_env(repo)
        docker = False
        try:
            check = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True, timeout=8, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            docker = check.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            pass
        keys = {key: bool(os.getenv(key)) for key in ("OPENAI_API_KEY", "DEEPSEEK_API_KEY")}
        provider = "DeepSeek" if model.startswith("deepseek") else "OpenAI"
        required_key = "DEEPSEEK_API_KEY" if provider == "DeepSeek" else "OPENAI_API_KEY"
        freeze_path = repo / "configs" / "freeze.json"
        freeze = None
        if freeze_path.exists():
            try:
                freeze = redact(json.loads(freeze_path.read_text(encoding="utf-8")))
            except ValueError:
                freeze = {"status": "invalid"}
        blockers = []
        if not docker:
            blockers.append("Docker engine unavailable. Start Docker Desktop and verify docker info.")
        if not keys[required_key]:
            blockers.append(f"No {provider} API key for the selected model. Add {required_key} to the local .env, then relaunch.")
        if not freeze or freeze.get("status") != "approved":
            blockers.append("Full experiments require the validated pilot and approved pre-run freeze.")
        budget = os.getenv("STUDY_BUDGET_USD")
        if not budget:
            blockers.append("No established study spending limit. Set STUDY_BUDGET_USD in the local .env before paid calls.")
        return {"docker_engine": docker, "provider_keys_present": keys, "selected_provider": provider, "required_key_present": keys[required_key], "study_budget_usd": budget, "freeze": freeze, "blockers": blockers, "note": "Presence checks do not verify provider access, credit, or actual testbed readiness. Runner validates these before collection."}

    @app.get("/api/jobs")
    def jobs():
        manager.discover_external()
        with manager.lock:
            return [manager.snapshot(j) for j in sorted(manager.jobs.values(), key=lambda j: j["created_at"], reverse=True)]

    @app.get("/api/configs/{name}")
    def configuration(name: str):
        if name not in {"engineering", "pilot", "study", "neutral-pilot", "enforcement-stress"}:
            raise HTTPException(404, "Unknown configuration preset")
        path = repo / "configs" / (name + ".json")
        try:
            return redact(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            raise HTTPException(404, "Configuration preset unavailable")

    @app.post("/api/jobs", status_code=202)
    def start(config: ExperimentConfig):
        load_local_env(repo)
        required_key = "DEEPSEEK_API_KEY" if config.model.startswith("deepseek") else "OPENAI_API_KEY"
        if config.mode == "llm" and not os.getenv(required_key):
            raise HTTPException(409, f"Real LLM mode requires {required_key} for the selected model in the dashboard process environment")
        if config.phase == "full":
            freeze_path = repo / "configs" / "freeze.json"
            try:
                freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                raise HTTPException(409, "No approved pre-run freeze. Complete and validate the pilot first.")
            if freeze.get("status") != "approved":
                raise HTTPException(409, "Pre-run freeze is not approved")
        return manager.start(config.model_dump(exclude_none=True))

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str):
        return manager.snapshot(manager.get(job_id))

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel(job_id: str):
        return manager.cancel(job_id)

    @app.post("/api/reset")
    def reset():
        with manager.lock:
            manager.discover_external()
            if any(j["status"] not in TERMINAL for j in manager.jobs.values()):
                raise HTTPException(409, "Cancel the running experiment before resetting the console")
        return {"status": "ready", "message": "Console reset. Each new run creates fresh experiment state. All raw observations and exports remain preserved."}

    @app.get("/api/jobs/{job_id}/runs")
    def runs(job_id: str):
        manager.path(job_id)
        return manager.compact_runs(job_id)

    def full_runs(job_id: str):
        # Explicit exports retain full summaries and label additive batch review.
        root = manager.path(job_id)
        quality = manager.quality(job_id)
        result = []
        for path in sorted((root / "runs").glob("*/summary.json")):
            try:
                resolved = safe_file(root, str(path.relative_to(root)))
                item = redact(json.loads(resolved.read_text(encoding="utf-8")))
                item["_batch_quality_status"] = quality["status"]
                item["_batch_quality_errors"] = quality["errors"]
                item["_batch_quality_assessments"] = quality["assessments"]
                item.setdefault("run_id", path.parent.name)
                item["summary_path"] = path.relative_to(root).as_posix()
                result.append(item)
            except (ValueError, OSError, HTTPException):
                continue
        return result

    @app.get("/api/jobs/{job_id}/files")
    def files(job_id: str, run_id: str | None = None, include_runs: bool = True):
        root = manager.path(job_id)
        result = []
        if run_id:
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
                raise HTTPException(404, "Unknown run")
            directory = (root / "runs" / run_id).resolve()
            if not directory.is_relative_to(root.resolve()) or not directory.is_dir():
                raise HTTPException(404, "Unknown run")
            candidates = directory.rglob("*")
        elif include_runs:
            candidates = root.rglob("*")
        else:
            # The browser lists batch/analysis files first and loads one run's
            # rotated traces on demand, avoiding tens of thousands of options.
            candidates = [*root.iterdir(), *(root / "analysis").rglob("*"), *(root / "figures").rglob("*"), *(root / "enforcement").rglob("*")]
        for path in sorted(candidates):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            try:
                safe_file(root, relative)
                result.append({"path": relative, "bytes": path.stat().st_size})
            except HTTPException:
                continue
        return result

    @app.get("/api/jobs/{job_id}/trace")
    def trace(job_id: str, path: str = "runner.log"):
        file = safe_file(manager.path(job_id), path)
        if file.stat().st_size > 4_000_000:
            raise HTTPException(413, "Trace exceeds 4 MB. Use the bundle export for the complete preserved data.")
        if file.name.endswith(".jsonl.gz"):
            content = bytearray()
            try:
                for chunk in sanitized_chunks(file):
                    content.extend(chunk)
                    if len(content) > 4_000_000:
                        raise HTTPException(413, "Decoded trace exceeds 4 MB. Use the bundle export.")
            except (OSError, ValueError) as error:
                raise HTTPException(422, "Invalid or oversized compressed JSONL evidence") from error
            content = bytes(content)
        else:
            content = sanitized_bytes(file)
        media_type = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml"}.get(file.suffix, "text/plain; charset=utf-8")
        return Response(content, media_type=media_type)

    @app.get("/api/jobs/{job_id}/export.json")
    def export_json(job_id: str):
        return Response(json.dumps(full_runs(job_id), indent=2), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{job_id}-runs.json"'})

    @app.get("/api/jobs/{job_id}/export.csv")
    def export_csv(job_id: str):
        rows = full_runs(job_id)
        out = io.StringIO(newline="")
        fields = sorted({k for row in rows for k in row})
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            values = {}
            for key, value in row.items():
                text = json.dumps(value) if isinstance(value, (dict, list)) else value
                if isinstance(text, str) and text.startswith(("=", "+", "-", "@")):
                    text = "'" + text
                values[key] = text
            writer.writerow(values)
        return Response(out.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{job_id}-runs.csv"'})

    @app.get("/api/jobs/{job_id}/bundle")
    def bundle(job_id: str):
        root = manager.path(job_id)
        job = manager.get(job_id)
        if job["status"] not in TERMINAL:
            raise HTTPException(409, "Finish or cancel collection before exporting a consistent bundle")
        export_dir = repo / ".runtime" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix=job_id + "-", suffix=".zip", dir=export_dir, delete=False) as temporary:
            archive_path = Path(temporary.name)
        manifest = {}
        altered = {}
        def add_file(archive, file, name):
            exported_hash, raw_hash = zip_sanitized(archive, file, name)
            manifest[name] = exported_hash
            if exported_hash != raw_hash:
                altered[name] = {"original_sha256": raw_hash, "exported_sha256": exported_hash,
                                 "reason": "Credential sanitization or text normalization changed exported bytes"}
        quality = manager.quality(job_id)
        collected_source = (root / "source").is_dir()
        source_files = set()
        try:
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
                for entry in files(job_id):
                    file = safe_file(root, entry["path"])
                    if entry["path"].startswith("source/"):
                        name = entry["path"]
                        source_files.add(entry["path"][len("source/"):])
                    else:
                        name = "results/" + entry["path"]
                    add_file(archive, file, name)
                # Sibling reviews are additive export copies, never inserted into raw data.
                for assessment in quality["assessments"]:
                    display = assessment["path"]
                    if display.startswith("external-quality/") and assessment.get("source_sha256"):
                        relative = display[len("external-quality/"):]
                        review = safe_file(manager.root, relative)
                        add_file(archive, review, "results/" + display)
                # A collected source snapshot takes precedence. Add only missing
                # instructions/support files under an explicit export-time label.
                prefix = "export-time-extras/" if collected_source else "source/"
                for folder in ("testbed", "analysis", "dashboard", "configs", "policies", "infra", "docs", "scripts", "tests"):
                    for file in sorted((repo / folder).rglob("*")):
                        if not file.is_file() or "__pycache__" in file.parts:
                            continue
                        relative = file.relative_to(repo).as_posix()
                        if relative in source_files:
                            continue
                        try:
                            safe_file(repo, relative)
                        except HTTPException:
                            continue
                        name = prefix + relative
                        add_file(archive, file, name)
                for filename in ("README.md", "requirements.txt", "requirements.lock", "requirements.lock.txt", "pyproject.toml", "compose.yaml", "docker-compose.yml", "Dockerfile", ".dockerignore", ".gitignore", ".env.example"):
                    file = repo / filename
                    if file.is_file() and filename not in source_files:
                        name = prefix + filename
                        add_file(archive, file, name)
                sealed = set()
                for seal in (root / "runs").glob("*/raw-manifest.json"):
                    for relative in json.loads(seal.read_text(encoding="utf-8"))["files"]:
                        sealed.add("results/" + (seal.parent / relative).relative_to(root).as_posix())
                altered_sealed = sorted(sealed.intersection(altered))
                provenance = {"schema": "dashboard-export-provenance-v1", "batch_quality": quality, "altered_files": altered,
                              "altered_sealed_members": altered_sealed,
                              "original_raw_manifests_preserved": not any(name.endswith("/raw-manifest.json") for name in altered),
                              "missing_sealed_members": sorted(sealed.difference(manifest)),
                              "raw_seal_validation": "NOT PERFORMED by exporter. Run analysis.cli --verify-raw on extracted results.",
                              "warning": "Original raw seals CANNOT validate altered exported members; sanitized data must not be claimed byte-identical raw evidence." if altered_sealed else "No sealed raw member required changed bytes. Independently verify raw seals after extraction."}
                provenance_bytes = json.dumps(provenance, indent=2).encode("utf-8")
                archive.writestr("EXPORT_PROVENANCE.json", provenance_bytes)
                manifest["EXPORT_PROVENANCE.json"] = hashlib.sha256(provenance_bytes).hexdigest()
                archive.writestr("SHA256SUMS.json", json.dumps(manifest, indent=2))
                source_note = "source/ contains the collection-time source snapshot; export-time-extras/ contains additional support files captured at export." if collected_source else "This legacy batch has no collection-time source snapshot. source/ was captured at export; use collection commit/freeze metadata to recover the original code."
                archive.writestr("BUNDLE_README.txt", "Sanitized reproducibility bundle. Raw sources remain unchanged locally. SHA256SUMS.json covers exported bytes. Clean gzip traces preserve their original compressed bytes after bounded inspection of every decoded record. EXPORT_PROVENANCE.json lists every changed file with original/exported hashes. Original raw manifests are retained: any altered sealed member will fail original raw-seal verification and must not be claimed raw-valid. The exporter does not certify raw validity. " + source_note + " Partial/cancelled evidence is retained and must not be treated as completed findings.\n")
            return FileResponse(archive_path, media_type="application/zip", filename=f"{job_id}-reproducibility.zip", background=BackgroundTask(archive_path.unlink, missing_ok=True))
        except Exception:
            archive_path.unlink(missing_ok=True)
            raise

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()
