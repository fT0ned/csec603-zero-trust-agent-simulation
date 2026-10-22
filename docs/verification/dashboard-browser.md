# Dashboard browser verification

Verified on October 22, 2026 through the in-app browser at `http://127.0.0.1:8765`, using the real Docker testbed. These are engineering checks with the scripted agent, kept separate from real LLM pilot and full-study findings.

1. Confirmed the readiness panel showed the running Docker engine and independently reported missing provider key, spending limit, and pre-run freeze at that time.
2. Selected real LLM mode with a placeholder model and a positive cap while no matching provider key was available. **Start experiment** was rejected before a batch was created. No paid call was made by this check.
3. Configured C0/S1, scripted mode, engineering phase, one trial. The browser started batch `20261022T110654-ba2544dc`, displayed running progress, then reported collection and analysis complete. Preserved run: `r83c71aaa9225435ba28844063a044bfc`.
4. Inspected the trial audit trace and descriptive condition comparison. Downloaded CSV, JSON, and the reproducibility ZIP through their actual browser controls. The downloaded CSV and JSON each contained the expected single C0 trial. Every one of the ZIP's 80 hashed exported files matched `SHA256SUMS.json`; the package included SPIRE configuration and the dependency lock. Later exports may contain additional files as implementation work continues; the source snapshot is taken at export time.
5. Clicked **Reset console**. Batch history and raw observations remained. The preserved trial summary had SHA-256 `d6d2cc08d0b078fe7e301ba6d41509df6ed0d69d65f2fee554d9c8898497e9c8` both before and after reset.
6. Configured C2/S2, scripted mode, engineering phase, one trial. The browser started batch `20261022T110822-0bbf459f` and displayed successful collection and analysis. Preserved run: `r143b417fcd3d4371b1962a051d008689`.
7. Inspected the C2 action trace. It contained actual SPIRE issuance metadata, OPA policy inputs and results, trusted origin and delegation fields, parameter provenance, and the careful-approver refusal. This confirms the dashboard reached the real control path; it does not establish real LLM injection susceptibility or full-study effectiveness.

Screenshots: [C0 evidence and comparison](dashboard-evidence.jpg), [C2 policy and issuance trace](dashboard-c2-policy.jpg).

The separate API suite verifies lifecycle behavior, retained raw files, redacted exports, Host/Origin/path boundaries, provider-specific prerequisites, cancellation and restart recovery, and SVG plot delivery. Its runner fixtures do not make paid calls and must not be counted as experimental trials.


## Final protocol and launch check

The final check used Edge and the actual `scripts/launch.ps1` wrapper, with no paid calls or container changes. Current server PID7944 listens on loopback8765. The full preset displayed32workers,90secondmargin and120secondtheft; backend/UI accept1–1800seconds. The CLI final-protocol batch's gzip trace decoded, JSON contained3trials and the ZIP had137members with valid exported checksums. Collected source CRLF bytes matched the original source hash; provider keys were absent and temporary ZIP files were removed. See dashboard-launch-wrapper.json and dashboard-launch-wrapper.jpg. The active real pilot002 was visible read-only and was not cancelled/reset by this check.
