"""Verify pilot-preserved experiment runtime bytes against the current source.

Analysis/dashboard presentation and the host-only freeze tool are outside this
comparison. The full-study freeze separately binds all required study files.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

from scripts.spire import ROOT


def selected(path: str) -> bool:
    return ((path.startswith("testbed/") and path != "testbed/freeze.py")
            or path.startswith("infra/")
            or path in {"scripts/spire.py", "scripts/tool_evidence.py", "compose.yaml", "Dockerfile", "requirements.txt", "requirements.lock.txt"})


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(pilot: Path) -> dict:
    manifest_path = pilot / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    preserved = {name.replace("\\", "/"): value for name, value in manifest["source_sha256"].items()}
    names = sorted(name for name in preserved if selected(name))
    if not names:
        raise RuntimeError("Pilot manifest contains no runtime source hashes")
    records = []
    for name in names:
        current = (ROOT / name).resolve()
        snapshot = (pilot / "source" / name).resolve()
        if not current.is_relative_to(ROOT.resolve()) or not snapshot.is_relative_to((pilot / "source").resolve()):
            raise ValueError("Pilot source path leaves its intended directory")
        current_hash = sha(current) if current.is_file() else None
        snapshot_hash = sha(snapshot) if snapshot.is_file() else None
        records.append({"path": name, "pilot_manifest_sha256": preserved[name],
                        "pilot_preserved_bytes_sha256": snapshot_hash, "current_bytes_sha256": current_hash,
                        "byte_match": current_hash == snapshot_hash == preserved[name]})
    extras = []
    for directory in ["testbed", "infra"]:
        for path in (ROOT / directory).rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            relative = path.relative_to(ROOT).as_posix()
            if selected(relative) and relative not in preserved:
                extras.append(relative)
    changed = [record["path"] for record in records if not record["byte_match"]]
    return {"verified_at": dt.datetime.now(dt.timezone.utc).isoformat(), "pilot": pilot.name,
            "pilot_manifest_sha256": sha(manifest_path), "pilot_mode": manifest["mode"], "pilot_phase": manifest["phase"],
            "hash_scheme": "SHA-256 of exact file bytes", "compared_file_count": len(records),
            "matched_file_count": sum(record["byte_match"] for record in records),
            "changed_or_missing_paths": changed, "extra_current_runtime_paths": sorted(extras), "files": records,
            "scope_note": "Experiment runtime, policies, topology, locked dependencies and identity/tool-evidence helpers; excludes host-only testbed/freeze.py and presentation/analysis files, which the final freeze binds separately.",
            "passed": not changed and not extras}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, default=ROOT / "results/pilot-002")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/verification/pilot-source-match.json")
    arguments = parser.parse_args()
    result = verify(arguments.pilot.resolve())
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "files"}, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
