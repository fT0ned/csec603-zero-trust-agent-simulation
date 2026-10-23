"""Restart isolated testbed sessions while preserving every host result and volume.

Never invoke during a collection: it interrupts all active tasks and credentials.
Fresh runs restore each mock service snapshot under a new run namespace. Existing
raw results, service audit volumes and historical mock namespaces remain retained.
"""
import json
from scripts.spire import bootstrap, compose


def reset():
    compose("down", timeout=120)
    identity = bootstrap()
    compose("up", "-d", "--wait", timeout=180)
    return {"status": "reset", "identity": identity,
            "preserved": ["host results", "host spending ledger", "Docker volumes", "service audit files"],
            "fresh_on_next_run": ["delegation", "workflow counters", "deny-list", "JIT grants", "mock data snapshot", "SPIRE registration", "credentials"]}


if __name__ == "__main__":
    print(json.dumps(reset(), indent=2))
