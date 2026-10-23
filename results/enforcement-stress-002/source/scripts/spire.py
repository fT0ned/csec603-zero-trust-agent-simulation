"""Trusted host SPIRE lifecycle; JWTs are returned in memory and never written.

Run ``python -m scripts.spire bootstrap`` before ``docker compose up -d --build``.
Bootstrap pins the server CA bundle; it does not use insecure agent bootstrapping.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import secrets
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "csec603.test"
NODE = f"spiffe://{DOMAIN}/node/experimental"
SERVER_SOCKET = "/run/spire/server/api.sock"
AGENT_SOCKET = "/run/spire/sockets/agent.sock"


def compose(*arguments: str, timeout: int = 60) -> str:
    completed = subprocess.run(["docker", "compose", *arguments], cwd=ROOT, text=True, capture_output=True, timeout=timeout, check=False)
    if completed.returncode:
        # Failed fetches contain diagnostics, never successful credentials.
        raise RuntimeError(f"Docker Compose command failed ({completed.returncode}): {completed.stderr.strip()[:2000]}")
    return completed.stdout


def _server(*arguments: str) -> str:
    return compose("exec", "-T", "spire-server", "/opt/spire/bin/spire-server", *arguments, "-socketPath", SERVER_SOCKET)


def _json_documents(raw: str) -> list[Any]:
    decoder, documents = json.JSONDecoder(), []
    rest = raw.strip()
    while rest:
        item, end = decoder.raw_decode(rest)
        documents.append(item)
        rest = rest[end:].strip()
    return documents


def _walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def bootstrap() -> dict[str, Any]:
    runtime = ROOT / ".runtime"
    bootstrap_dir = runtime / "bootstrap"
    bootstrap_dir.mkdir(parents=True, exist_ok=True)
    secret_file = runtime / "control.env"
    if not secret_file.exists():
        secret_file.write_text("ADMIN_SECRET=" + secrets.token_urlsafe(48) + "\n", encoding="utf-8")
    compose("up", "-d", "spire-server", timeout=120)
    for attempt in range(60):
        try:
            _server("healthcheck")
            break
        except RuntimeError:
            if attempt == 59:
                raise
            time.sleep(1)
    bundle = _server("bundle", "show", "-format", "pem")
    if "-----BEGIN CERTIFICATE-----" not in bundle:
        raise RuntimeError("SPIRE did not provide a PEM trust bundle")
    token_output = _server("token", "generate", "-spiffeID", NODE, "-ttl", "600", "-output", "json")
    nodes = list(_walk(_json_documents(token_output)))
    token = next((n.get("token", n.get("value")) for n in nodes if isinstance(n, dict) and isinstance(n.get("token", n.get("value")), str)), None)
    if not token:
        raise RuntimeError("SPIRE join token was missing in response")
    (bootstrap_dir / "bundle.pem").write_text(bundle, encoding="ascii")
    (bootstrap_dir / "join-token").write_text(token, encoding="ascii")
    compose("up", "-d", "spire-agent", timeout=120)
    return {"status": "bootstrapped", "trust_domain": DOMAIN, "node_id": NODE,
            "trust_bundle_sha256": hashlib.sha256(bundle.encode()).hexdigest(), "identity": "actual SPIRE; join-token node attestation and Unix UID workload attestation"}


def issue(run_id: str, ttl_seconds: int) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", run_id):
        raise ValueError("Unsafe run ID")
    if not isinstance(ttl_seconds, int) or ttl_seconds < 1 or ttl_seconds > 3600:
        raise ValueError("JWT TTL must be 1..3600 seconds; headline lifetimes are 300/900/3600")
    spiffe_id = f"spiffe://{DOMAIN}/agent/{run_id}"
    entry_id = ""
    registered = _server("entry", "create", "-parentID", NODE, "-spiffeID", spiffe_id,
                         "-selector", "unix:uid:10001", "-jwtSVIDTTL", str(ttl_seconds), "-output", "json")
    for node in _walk(_json_documents(registered)):
        if isinstance(node, dict) and isinstance(node.get("id"), str):
            entry_id = node["id"]
            break
    if not entry_id:
        raise RuntimeError("SPIRE registration response had no entry ID")
    try:
        for attempt in range(30):
            try:
                output = compose("exec", "-T", "agent-client", "/opt/spire/bin/spire-agent", "api", "fetch", "jwt",
                                 "-socketPath", AGENT_SOCKET, "-audience", "csec603-gateway", "-spiffeID", spiffe_id, "-output", "json")
                nodes = list(_walk(_json_documents(output)))
                token = next((n.get("svid") for n in nodes if isinstance(n, dict) and isinstance(n.get("svid"), str)), None)
                jwks = None
                for node in nodes:
                    if isinstance(node, dict) and isinstance(node.get("bundles"), dict):
                        encoded = node["bundles"].get(f"spiffe://{DOMAIN}", node["bundles"].get(DOMAIN))
                        if isinstance(encoded, str):
                            try:
                                jwks = json.loads(base64.b64decode(encoded))
                            except (ValueError, json.JSONDecodeError):
                                jwks = json.loads(encoded)
                if not token or not jwks:
                    raise RuntimeError("SPIRE response did not contain token and trust-domain JWKS")
                claims = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "==="))
                observed_lifetime = claims["exp"] - time.time()
                if claims.get("sub") != spiffe_id or not ttl_seconds - 30 <= observed_lifetime <= ttl_seconds + 3:
                    raise RuntimeError("Issued identity or lifetime differs from registration")
                return {"token": token, "credential_id": hashlib.sha256(token.encode()).hexdigest(), "spiffe_id": spiffe_id,
                        "entry_id": entry_id, "jwks": jwks, "claims": claims, "issuer": "spire",
                        "attestation": {"node_id": NODE, "node_mechanism": "join_token", "workload_selector": "unix:uid:10001",
                                        "requested_ttl_seconds": ttl_seconds, "issued_at_observed": time.time(), "version": "1.14.1"}}
            except RuntimeError:
                if attempt == 29:
                    raise
                time.sleep(1)
    except BaseException:
        delete_registration(entry_id)
        raise


def delete_registration(entry_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9-]+", entry_id):
        raise ValueError("Unsafe registration ID")
    _server("entry", "delete", "-entryID", entry_id)


cleanup = delete_registration


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["bootstrap"])
    parser.parse_args()
    print(json.dumps(bootstrap(), indent=2))
