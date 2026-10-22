"""Read independent committed tool state through trusted host Docker access.

No tool service or gateway audit record is accepted as the sole outcome oracle.
Only the trusted harness invokes these local service evidence endpoints; neither
agent nor attacker has a route to the private tools network or a Docker socket.
"""
from __future__ import annotations

import concurrent.futures
import json
import re
import subprocess
from typing import Any

from scripts.spire import ROOT

TOOLS = ("files", "email", "crm", "payments")


def _one(tool: str, run_id: str) -> tuple[str, dict[str, Any]]:
    program = "import json,sys,urllib.request; run_id=json.load(sys.stdin)['run_id']; print(urllib.request.urlopen('http://127.0.0.1:8000/evidence/'+run_id,timeout=10).read().decode())"
    result = subprocess.run(["docker", "compose", "exec", "-T", tool, "python", "-c", program],
                            input=json.dumps({"run_id": run_id}), cwd=ROOT, capture_output=True,
                            text=True, timeout=30, check=False)
    if result.returncode:
        raise RuntimeError(f"Independent {tool} evidence could not be collected: {result.stderr[-1000:]}")
    try:
        data = json.loads(result.stdout)
    except ValueError as error:
        raise RuntimeError(f"Independent {tool} evidence was not JSON") from error
    if not isinstance(data.get("state"), dict) or not isinstance(data.get("write_calls"), list):
        raise RuntimeError(f"Independent {tool} evidence schema was invalid")
    return tool, data


def snapshot(run_id: str) -> dict[str, dict[str, Any]]:
    """Collect each service's durable state, failing if any source is unavailable."""
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,200}", run_id):
        raise ValueError("Unsafe run ID")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        return dict(pool.map(lambda tool: _one(tool, run_id), TOOLS))
