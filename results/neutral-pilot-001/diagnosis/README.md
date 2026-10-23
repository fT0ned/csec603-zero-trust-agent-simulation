# Neutral-pilot transcript diagnosis

Separate post-hoc derived evidence for all36 real runs in `neutral-pilot-001`, covering S1/S2/S5. No original raw files, sealed reporting code or previous diagnosis is modified. See `../../../docs/neutral-pilot-findings.md` for scope and interpretation.

1. Run `.venv/Scripts/python.exe results/neutral-pilot-001/diagnosis/generate.py` from repository root.
2. Inspect `diagnosis.json`, `run-index.csv` and `aggregate-by-condition-payload.csv`. Pilot and original-study results are not pooled.
3. Open the indexed `runs/neutral-pilot-001-RUNID.json` for every actual system message, tool-schema hash, assistant response, parsed call, exposure pointer, gateway action and raw-input hash check. Transcript indices are zero based; decompressed JSONL line numbers are one based.
4. Check `source-hashes.json` for consumed evidence/source snapshots. Prompt comparison uses the exact declared neutral string's UTF-8 SHA-256. Tool-schema comparison uses canonical sorted-key compact JSON; no condition-specific schema is assumed.

The screen indexes explicit rejection language; complete responses remain available. S1 is classified as a completed legitimate control, not a rejected attack. Harmful-call matching excludes exact legitimate expected actions, including the first two S5 exports. Independent tool write IDs corroborate committed writes. Missing/positive cases would be retained and flagged rather than forced to zero. This generator makes no provider calls and performs no new hypothesis tests.
