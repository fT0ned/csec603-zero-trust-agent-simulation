"""Measure actual issuance, HTTP health and container isolation without an LLM call."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import time
import uuid
from pathlib import Path
from urllib.request import urlopen

import jwt

from scripts.spire import ROOT, compose, delete_registration, issue


def _container_ip(service: str, network: str) -> str:
    identifier = compose("ps", "-q", service).strip()
    output = subprocess.run(["docker", "inspect", identifier], text=True, capture_output=True, check=True).stdout
    return json.loads(output)[0]["NetworkSettings"]["Networks"]["csec603-testbed_" + network]["IPAddress"]


def verify() -> dict:
    evidence = {"verified_at": dt.datetime.now(dt.timezone.utc).isoformat(), "classification": "engineering verification; not real-LLM findings", "checks": {}}
    http_clocks = []
    for name, port in [("gateway", 8766), ("pa", 8767)]:
        for sample in range(5):
            before = time.time()
            health = json.loads(urlopen(f"http://127.0.0.1:{port}/health", timeout=5).read())
            after = time.time()
            if not isinstance(health.get("time"), (int, float)):
                raise RuntimeError("Rebuild gateway/PA to expose server epoch time before clock verification")
            low, high = health["time"] - after, health["time"] - before
            http_clocks.append({"service": name, "sample": sample, "host_before": before, "server_time": health["time"],
                                "host_after": after, "offset_lower_seconds": low, "offset_upper_seconds": high,
                                "roundtrip_seconds": after-before, "permitted_absolute_offset_bound_seconds": 1,
                                "passed": low >= -1 and high <= 1})
        evidence["checks"][name + "_health"] = health
    if not all(row["passed"] for row in http_clocks):
        raise RuntimeError("HTTP clock-offset bound exceeds one second; synchronize host and Docker clocks before timing experiments")
    evidence["checks"]["http_clock_offset_brackets"] = http_clocks
    targets = [("gateway", _container_ip("gateway", "front"), 8000, True)]
    for name in ["files", "email", "crm", "payments"]:
        targets.append((name, _container_ip(name, "tools"), 8000, False))
    targets.extend([("pa", _container_ip("pa", "control"), 8000, False),
                    ("opa", _container_ip("opa", "control"), 8181, False),
                    ("spire-server", _container_ip("spire-server", "identity"), 8081, False)])
    program = """import json,socket,sys,pathlib
r=[]
for name,ip,port,expected in json.load(sys.stdin):
 try:
  s=socket.create_connection((ip,port),0.4);s.close();actual=True
 except OSError:actual=False
 r.append({'target':name,'reachable':actual,'expected_reachable':expected,'passed':actual==expected})
print(json.dumps({'connections':r,'workload_socket_present':pathlib.Path('/run/spire/sockets/agent.sock').exists()}))
"""
    result = subprocess.run(["docker", "compose", "exec", "-T", "attacker", "python", "-c", program], input=json.dumps(targets), cwd=ROOT, text=True, capture_output=True, timeout=20, check=True)
    isolation = json.loads(result.stdout)
    if not all(row["passed"] for row in isolation["connections"]) or isolation["workload_socket_present"]:
        raise RuntimeError("Attacker network or workload-socket isolation failed")
    evidence["checks"]["attacker_isolation"] = isolation
    clocks = []
    for name in ["gateway", "pa", "agent-client", "attacker", "files", "email", "crm", "payments"]:
        before = time.time()
        container_time = float(compose("exec", "-T", name, "python", "-c", "import time; print(time.time())").strip())
        after = time.time()
        low, high = container_time - after, container_time - before
        # The measurement brackets the clock offset; execution/transport latency
        # widens this interval and is never interpreted as measured clock drift.
        passed = low >= -1 and high <= 1
        clocks.append({"service": name, "host_before": before, "container_time": container_time, "host_after": after,
                       "offset_lower_seconds": low, "offset_upper_seconds": high, "roundtrip_seconds": after-before,
                       "permitted_absolute_offset_bound_seconds": 1, "passed": passed})
    if not all(row["passed"] for row in clocks):
        raise RuntimeError("Clock-offset uncertainty exceeds one second; synchronize clocks or retry when Docker is responsive before timing experiments")
    evidence["checks"]["clock_offset_brackets"] = clocks
    environment_checks = []
    for name in ["gateway", "pa", "agent-client", "attacker", "files", "email", "crm", "payments"]:
        identifier = compose("ps", "-q", name).strip()
        inspect = json.loads(subprocess.run(["docker", "inspect", identifier], text=True, capture_output=True, check=True).stdout)[0]
        environment_names = [value.split("=", 1)[0] for value in inspect["Config"]["Env"]]
        forbidden = [key for key in environment_names if any(term in key.upper() for term in ["OPENAI", "ANTHROPIC", "DEEPSEEK", "API_KEY", "STUDY_BUDGET"])]
        passed = not forbidden and (name in ["gateway", "pa"] or "ADMIN_SECRET" not in environment_names)
        environment_checks.append({"service": name, "provider_credential_variable_names": forbidden,
                                   "administrator_secret_expected": name in ["gateway", "pa"], "passed": passed})
    if not all(row["passed"] for row in environment_checks):
        raise RuntimeError("A client or tool received control-plane/provider credentials")
    evidence["checks"]["credential_separation"] = environment_checks
    lifetimes = []
    for ttl in [300, 900, 3600]:
        credential = issue("verify-" + uuid.uuid4().hex, ttl)
        try:
            header = jwt.get_unverified_header(credential["token"])
            key = next(k for k in credential["jwks"]["keys"] if k["kid"] == header["kid"])
            claims = jwt.decode(credential["token"], jwt.PyJWK.from_dict(key).key, algorithms=["ES256"], audience="csec603-gateway")
            actual = claims["exp"] - claims["iat"]
            if actual != ttl:
                raise RuntimeError("Actual JWT claim lifetime does not match the requested registration lifetime")
            lifetimes.append({"requested_seconds": ttl, "measured_claim_lifetime_seconds": actual, "signature_and_audience_validated": True,
                              "attestation": credential["attestation"], "credential_id": credential["credential_id"]})
        finally:
            delete_registration(credential["entry_id"])
    evidence["checks"]["spire_issuance"] = lifetimes
    evidence["passed"] = True
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = verify()
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
