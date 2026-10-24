"""Dashboard-compatible analysis entrypoint and sealed raw-file verifier."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .run import analyze


def verify_raw(root):
    """Validate every run's raw manifest without modifying collected artifacts.

    Current harness manifests hash decoded UTF-8 text after universal newline
    normalization. The verifier labels this legacy contract explicitly and also
    reports each file's byte SHA-256. New byte manifests can declare their scheme.
    """
    root=Path(root).resolve()
    runs=root/"runs"
    folders=sorted(p for p in runs.iterdir() if p.is_dir()) if runs.is_dir() else []
    result={"valid":True,"runs":len(folders),"files_checked":0,"errors":[],"warnings":[],"files":[]}
    if not folders:
        result["errors"].append({"path":str(runs),"reason":"No run directories found"})
    for folder in folders:
        manifest_path=folder/"raw-manifest.json"
        if not manifest_path.is_file():
            result["errors"].append({"path":str(manifest_path),"reason":"Raw manifest missing"});continue
        try:
            manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
            scheme=manifest.get("hash_scheme","sha256-utf8-universal-newlines")
            files=manifest.get("files",manifest)
            if scheme not in ("sha256-bytes","sha256-utf8-universal-newlines"):
                raise ValueError("Unknown raw hash scheme: "+str(scheme))
            if not isinstance(files,dict):raise ValueError("Manifest files must be an object")
            for relative,expected in files.items():
                path=(folder/relative).resolve()
                if not path.is_relative_to(folder.resolve()) or path == manifest_path.resolve():
                    raise ValueError("Manifest path escapes run or refers to itself: "+relative)
                if not path.is_file():
                    result["errors"].append({"path":str(path),"reason":"Sealed file missing"});continue
                data=path.read_bytes();byte_hash=hashlib.sha256(data).hexdigest()
                actual=byte_hash if scheme == "sha256-bytes" else hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
                result["files_checked"]+=1
                result["files"].append({"path":str(path),"sha256_bytes":byte_hash,"manifest_scheme":scheme,"matches":actual==expected})
                if actual!=expected:result["errors"].append({"path":str(path),"reason":"Sealed file hash mismatch"})
            extras=sorted(str(p.relative_to(folder)) for p in folder.iterdir()
                          if p.is_file() and p.name!="raw-manifest.json" and str(p.relative_to(folder)) not in files)
            if extras:result["warnings"].append({"run":folder.name,"reason":"Unsealed added files","files":extras})
        except (OSError,ValueError,TypeError,AttributeError) as exc:
            result["errors"].append({"path":str(manifest_path),"reason":str(exc)})
    result["valid"]=not result["errors"]
    result["scope"]="Verifies listed run files only; protects no trust boundary if an attacker can replace both files and manifest. Ground-truth/checkpoint isolation is separately required."
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",required=True,type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--bootstrap-samples",type=int,default=2000)
    parser.add_argument("--verify-raw",action="store_true",help="Verify sealed raw files before analysis; exit 2 on mismatch")
    args=parser.parse_args(argv)
    if args.bootstrap_samples<100:parser.error("Use at least 100 bootstrap resamples")
    output=args.output or args.input/"analysis"
    verification=verify_raw(args.input) if args.verify_raw else None
    if verification is not None:
        output.mkdir(parents=True,exist_ok=True)
        (output/"raw-verification.json").write_text(json.dumps(verification,indent=2),encoding="utf-8")
        if not verification["valid"]:
            print(json.dumps({"status":"raw_verification_failed","errors":len(verification["errors"]),"output":str(output)}))
            return 2
    report=analyze(args.input,output,args.bootstrap_samples)
    print(json.dumps({"status":"completed" if not report["load_errors"] else "load_errors",
                      "runs":report["runs"],"load_errors":len(report["load_errors"]),"output":str(output),
                      "raw_verified":verification["valid"] if verification is not None else None}))
    return 0 if not report["load_errors"] else 2


if __name__ == "__main__":raise SystemExit(main())
