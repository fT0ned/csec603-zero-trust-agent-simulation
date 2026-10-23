"""Verify the running image and live controls without rebuilding or restarting.

Only this verifier's fresh task namespaces are retired. Preserved service audit
files, tool snapshots, provider spending records and experiment outputs survive.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import subprocess

from scripts.spire import ROOT, compose
from scripts import verify_controls
from scripts.verify_infra import verify


def source_image_match() -> dict:
    paths = sorted([str(path.relative_to(ROOT)).replace("\\", "/") for path in (ROOT / "testbed").glob("*.py")]
                   + ["infra/tools.py", "infra/opa/policy.rego", "scripts/spire.py", "scripts/tool_evidence.py"])
    expected = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
    program = "import hashlib,json,pathlib,sys; paths=json.load(sys.stdin); print(json.dumps({p:hashlib.sha256((pathlib.Path('/app')/p).read_bytes()).hexdigest() for p in paths}))"
    measured = subprocess.run(["docker", "compose", "exec", "-T", "gateway", "python", "-c", program],
                              input=json.dumps(paths), cwd=ROOT, text=True, capture_output=True, timeout=30, check=True)
    actual = json.loads(measured.stdout)
    mismatches = [path for path in paths if actual.get(path) != expected[path]]
    services = {}
    for name in ["gateway", "pa", "agent-client", "attacker", "files", "email", "crm", "payments"]:
        identifier = compose("ps", "-q", name).strip()
        inspected = subprocess.run(["docker", "inspect", identifier], text=True, capture_output=True, timeout=15, check=True)
        metadata = json.loads(inspected.stdout)[0]
        services[name] = {"container_id": metadata["Id"], "image_id": metadata["Image"],
                          "health": metadata["State"].get("Health", {}).get("Status")}
    same_image = len({item["image_id"] for item in services.values()}) == 1
    healthy = all(item["health"] == "healthy" for item in services.values())
    result = {"verified_at": dt.datetime.now(dt.timezone.utc).isoformat(), "host_source_sha256": expected,
              "deployed_source_sha256": actual, "mismatches": mismatches, "services": services,
              "same_app_image_for_all_services": same_image, "all_app_services_healthy": healthy,
              "passed": not mismatches and same_image and healthy}
    return result


def write_evidence(name: str, value: dict):
    path = ROOT / "docs" / "verification" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main():
    previous = ROOT / "docs/verification/final-live.json"
    if previous.exists():
        old = json.loads(previous.read_text(encoding="utf-8"))
        stamp = old["verified_at"].replace(":", "").replace("+", "_")
        history = ROOT / "docs/verification/history" / stamp
        history.mkdir(parents=True, exist_ok=True)
        for name in ["source-image.json", "infrastructure.json", "controls.json", "final-live.json"]:
            source = previous.parent / name
            target = history / name
            if source.exists() and not target.exists():
                shutil.copyfile(source, target)
    result = {"verified_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "classification": "actual live engineering verification; no LLM calls or research findings"}
    sources = source_image_match()
    write_evidence("source-image.json", sources)
    result["source_image_passed"] = sources["passed"]
    if not sources["passed"]:
        result.update(passed=False, diagnostic_reason="Deployed application source/image differs from the host source or is unhealthy",
                      mismatched_paths=sources["mismatches"])
        write_evidence("final-live.json", result)
        raise RuntimeError(result["diagnostic_reason"])
    infrastructure = verify()
    write_evidence("infrastructure.json", infrastructure)
    result["infrastructure_passed"] = infrastructure["passed"]
    created = []
    original_post = verify_controls.admin_post

    def track_post(path, data=None):
        response = original_post(path, data)
        if path == "/control/runs":
            created.append(data["run_id"])
        return response

    verify_controls.admin_post = track_post
    cleanup = []
    try:
        verify_controls.main()
        controls = json.loads((ROOT / "docs/verification/controls.json").read_text(encoding="utf-8"))
        result["controls_passed"] = controls["passed"]
    finally:
        verify_controls.admin_post = original_post
        for run_id in created:
            try:
                response = original_post("/control/" + run_id + "/retire")
                cleanup.append({"run_id": run_id, "retired": response.get("retired") == run_id,
                                "audit_preserved": response.get("audit_preserved")})
            except Exception as error:
                cleanup.append({"run_id": run_id, "retired": False, "error_type": type(error).__name__})
        result["verification_namespace_cleanup"] = cleanup
        result["passed"] = all(result.get(key, False) for key in ["source_image_passed", "infrastructure_passed", "controls_passed"]) and all(row["retired"] for row in cleanup)
        write_evidence("final-live.json", result)
    if not result["passed"]:
        raise RuntimeError("Final live verification or cleanup failed")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
