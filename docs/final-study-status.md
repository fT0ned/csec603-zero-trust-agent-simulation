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
