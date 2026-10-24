"""Verify isolation from resolved Compose configuration and tool effects."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from infra import tools
from scripts.spire import _json_documents

ROOT = Path(__file__).resolve().parents[1]


def test_compose_trust_boundaries():
    if not shutil.which("docker") or not (ROOT / ".runtime/control.env").exists():
        pytest.skip("Docker Compose or bootstrap control file unavailable")
    result = subprocess.run(["docker", "compose", "config", "--format", "json"], cwd=ROOT, capture_output=True, text=True, check=True)
    config = json.loads(result.stdout)
    services = config["services"]
    for tool in ["files", "email", "crm", "payments"]:
        assert not services[tool].get("ports")
        assert set(services[tool]["networks"]) == {"tools"}
    assert config["networks"]["tools"]["internal"]
    assert config["networks"]["control"]["internal"]
    assert config["networks"]["identity"]["internal"]
    assert set(services["attacker"]["networks"]) == {"front"}
    assert not services["attacker"].get("volumes")
    assert not services["attacker"].get("ports")
    assert not services["agent-client"].get("ports")
    assert services["agent-client"]["user"] == "10001:10001"
    assert services["attacker"]["user"] == "10002:10002"
    for service in ["gateway", "pa"]:
        assert all(port["host_ip"] == "127.0.0.1" for port in services[service]["ports"])
    assert set(services["opa"]["networks"]) == {"control"}
    assert not services["opa"].get("ports")
    for service in ["spire-server", "spire-agent", "opa"]:
        assert "@sha256:" in services[service]["image"]


def test_mock_tools_reset_idempotence_and_actual_effects(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "DB", tmp_path / "crm.db")
    monkeypatch.setattr(tools, "KIND", "crm")
    client = TestClient(tools.app)
    assert client.post("/reset", json={"run_id": "first", "content": "Safe fixture"}).status_code == 200
    payload = {"run_id": "first", "request_id": "a", "action": "crm.export", "params": {"offset": 0, "limit": 5}}
    first = client.post("/execute", json=payload)
    assert first.status_code == 200
    assert first.json()["records"] == 5
    assert client.post("/execute", json=payload).json() == first.json()
    assert len(client.get("/state/first").json()["exports"]) == 5
    read = {"run_id": "first", "request_id": "read", "action": "crm.read", "params": {"offset": 0, "limit": 1}}
    assert client.post("/execute", json=read).status_code == 200
    evidence = client.get("/evidence/first").json()
    assert len(evidence["write_calls"]) == 1
    assert evidence["write_calls"][0]["request_id"] == "a"
    assert evidence["write_calls"][0]["params"] == {"offset": 0, "limit": 5}
    assert evidence["write_calls"][0]["response"] == first.json()
    assert len(evidence["state"]["exports"]) == 5
    assert client.get("/evidence/not-a-run").status_code == 404
    payload["params"]["limit"] = 4
    assert client.post("/execute", json=payload).status_code == 409
    assert client.post("/reset", json={"run_id": "second"}).status_code == 200
    assert client.get("/state/second").json()["exports"] == []
    assert client.get("/evidence/second").json()["write_calls"] == []
    assert len(client.get("/state/first").json()["exports"]) == 5
    payload["request_id"] = "negative"
    payload["params"]["limit"] = -1
    assert client.post("/execute", json=payload).status_code == 422
    assert len(client.get("/state/first").json()["exports"]) == 5


def test_mock_payment_and_email_are_simulated_effects(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "DB", tmp_path / "payments.db")
    monkeypatch.setattr(tools, "KIND", "payments")
    client = TestClient(tools.app)
    client.post("/reset", json={"run_id": "pay"})
    response = client.post("/execute", json={"run_id": "pay", "request_id": "one", "action": "payments.pay", "params": {"vendor": "vendor-1", "amount": 25, "invoice": "invoice-mock"}})
    assert response.json()["amount"] == 25
    assert response.json()["state"]["payment_total"] == 25
    assert client.get("/state/pay").json()["payments"][0]["invoice"] == "invoice-mock"


def test_spire_stream_json_parser():
    assert _json_documents('{"svids": []}\n{"bundles": {}}') == [{"svids": []}, {"bundles": {}}]


def test_real_opa_policy_semantics():
    if not shutil.which("docker"):
        pytest.skip("Docker unavailable")
    image = "openpolicyagent/opa:1.10.1-static@sha256:e1f196b5316301785d5251543c9d0f3f6c83ce6ac23263b494730427fa80e248"
    present = subprocess.run(["docker", "image", "inspect", image], capture_output=True)
    if present.returncode:
        pytest.skip("Pinned OPA image not present; setup pulls it")
    result = subprocess.run(["docker", "run", "--rm", "-v", str(ROOT / "infra/opa") + ":/policies:ro", image, "test", "/policies"], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS: 8/8" in result.stdout
