# Original-agent transcript diagnosis

Post-hoc descriptive audit of every S2/S5 run in `pilot-002` and `study-002`. This directory is a separate derived artifact; it does not edit either collection or the frozen analysis. See `../../docs/diagnosis-original-agent.md` for interpretation and limits.

1. From the repository root run `.venv/Scripts/python.exe results/diagnosis-original/generate.py`. The program performs only local reads of the selected original inputs and writes this derived directory; it makes no model/API calls.
2. Read `diagnosis.json` for collection/scenario counts, explicit classification rule and reconciliation issues. Pilot and full counts remain separate.
3. Use `run-index.csv` for all 340 per-run classifications and `aggregate-by-condition-payload.csv` for all 60 collection/condition/payload groups. Run detail filenames are in the index.
4. Open `runs/COLLECTION-RUNID.json` for the complete assistant responses, model tool calls, actual gateway actions, exposure pointers, rejection excerpts, source hashes and independently confirmed write counts. Indices into `transcript.json` are zero based; source JSONL line numbers are one based after decompression.
5. Compare every consumed raw input against its hash in `source-hashes.json`. Each run detail also compares summary, fixture, transcript, action and independent tool-state files against that run's existing byte-hash manifest. This is selected-input verification, not a replacement for the complete batch validation or an independent signature of the manifest.

The rejection phrase screen is an evidence index, not a validated classifier of model cognition. It labels observable text only, and complete responses are retained so each decision can be checked. The script separately reconstructs the frozen harmful-call predicate from the preserved fixture, checks outgoing model calls against gateway attempts, and checks committed writes against independent tool evidence. No security-outcome-based exclusions or new hypothesis tests are performed.
