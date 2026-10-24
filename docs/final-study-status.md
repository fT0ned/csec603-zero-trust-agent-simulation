# final-study-001 status (durable resume file)

Updated at each milestone. Protocol: `docs/final-study-protocol.md`. Orchestrator: `testbed/final_study.py`; collector: `scripts/collect_final_study.py`.

## Milestones
- [x] Orchestrator, configs, tests (commit "Add final-study orchestrator ...").
- [x] UTF-8 container request fix (first pilot attempt failed on an em dash; attempt discarded).
- [x] Protocol doc written before data.
- [x] Pilot `results/final-study-pilot-001` 134/134, `docs/final-study-pilot-review.md` (commit 67e2d0c3).
- [x] Analyzer `analysis/final_study.py` verified on pilot data.
- [x] Freeze `configs/final-study-freeze.json`, annotated tag `final-study-freeze-v1`, pushed (commit fedd511b).
- [~] Full collection `results/final-study-001` STARTED (3,090 runs). Stage 1: Parts B+C (4+8 workers); stage 2: Part A (32 workers). Collector PID 44540 (launcher 43660). Log `.runtime/final-001.log`.
- [ ] Timing reruns (if any), quality.json, analysis, findings, paper tables, easyboard, README/progress.

## How to resume
- Pilot/full run command: `.venv/Scripts/python.exe -m scripts.collect_final_study run --config configs/final-study.json --output results/final-study-001`
- After an interruption: same command plus `--resume` (identical config required; crashed `running` units are kept, cells without a usable terminal run are re-executed, infrastructure failures get one linked rerun).
- Progress: `results/final-study-001/final-progress.json`; log: `.runtime/final-001.log`.
- After collection: `... collect_final_study timing-reruns --config ... --output ...`, then `.venv/Scripts/python.exe -m analysis.final_study --input results/final-study-001 --output results/final-study-001/analysis`.
- Containers must be healthy and byte-identical to source (`docker compose build && docker compose up -d`); the run verifies this itself.
- Never edit `.env` ledger entries or `.runtime/spend.sqlite`; budget changes only via `STUDY_BUDGET_USD` in the ignored `.env` (max 15), recorded below.

## Budget
Ledger before this work: USD 0.7686 of a 4.00 cap (STUDY_BUDGET_USD=4). No change yet.

## Part A infrastructure failures observed during collection (checked read-only)
At 776/2100 Part A units, 4 units were `infrastructure_failure`, all C0/C1 S4 (not systematic by condition/TTL: C0 300 now, C0 300 expiry, C0 900 expiry, C1 3600 now). Causes: (1) one PA `/control/runs` HTTP 500 (transient tool-reset connection error, 19:38); (2) two `docker compose exec` CLI crashes (Go runtime stack traces from the Docker CLI, 20:28, host load) in container_request / tool-evidence snapshot; (3) one `tool_failure` probe measurement error (20:35). All containers healthy. These are covered by the frozen rule (one linked infrastructure rerun per cell, originals kept); the orchestrator performs them automatically at the end of stage 2. No code change made. Risk: more Docker CLI crashes under 32-way load; if remaining failures after reruns are nonzero they are reported as such, never hidden.
