# Durable engineering progress

Updated 2026-10-22 (Asia/Dubai), resumed after account usage pause.

## Authority and fixed design
Read complete governing Word text and its embedded control-path diagram, all five Phase2/0Documentation documents, and docs/research-brief.md. Source text extracts and figure are outside Git at ../source-review. Official requirements/professor feedback prevail. Preserve original RQs, C0/C1/C2, C2-noWF/C2-RS on S2/S5, all five scenarios, actual SPIRE bearer credentials, common revocation deny-list and real-time TTLs300/900/3600.

## Completed evidence
- Python3.12 .venv installed from pinned transitive requirements.lock.txt; Docker29.8.2 engine running.
- Actual SPIRE1.14.1 JWT-SVID issuance/signature/audience and all three TTLs verified. OPA1.10.1 policy tests pass. Attack client isolated from tools/control/issuer.
- Live atomic workflow, forged authority, cached-replay revocation, approval ablation and fresh reset checks passed.
- results/engineering-001:88 actual scripted engineering runs completed, all raw integrity checks pass; NOT real-LLM findings. Early engineering source was uncommitted; later batches preserve source snapshots and freeze metadata.
- Browser full workflow (C0/S1 and C2/S2): start/progress/results/traces/CSV/JSON/ZIP/reset verified, export member hashes checked, screenshots in docs/verification.
- Latest local suite37passed. No measured paid pilot yet.

## Provider and spending
A new ignored APIKEY_GENAI_USETHIS.txt handoff appeared. Imported only its DeepSeek key to ignored .env; neither key nor file may enter Git. Read-only /user/balance and /models succeeded:4.93USD prepaid at access check. Under user's full implementation autonomy, set conservative total STUDY_BUDGET_USD=4 with no topup. Persistent shared SQLite spending reservations in .runtime/spend.sqlite bound all workers/batches; never reset this ledger. Official DeepSeek docs checked current deepseek-flash -> documented DeepSeek-V4.1-Flash-1017, mutable API alias; temperature0, thinking disabled. Usage/cache/time-based costs and uncertainty are preserved. No provider fallback.

## Current assignments and pending work
- Infra agent rebuilding latest service/tool-evidence image and rechecking live topology/controls. Do not start before READY.
- Dashboard agent finishing scalable streamed ZIP exports, gzip trace decoding, DeepSeek UI/restart/browser QA.
- Analysis agent finishing hypothesis assessments and supplemental intent-violation outcomes.
- Lead: runner measurement corrections, independent committed tool-state success oracle, compressed/chunked read-only raw data, freeze gating, setup/launch/reproduction docs; paid pilot then freeze/fullstudy.

## Runner changes since first engineering batch
Reachability now checked before expiration observation. Harmless baseline proves credential validity; S4 now/expiry share security-decision timestamp, first denial uses client observation time. Observation deadline absolute and perTTL min(configwindow,TTL+5). Provider/model errors retained without infrastructure reruns. PA reserves workflow allowance before downstream call (unknown tool outcome retains reservation). Service audit/provenance/cache bounded in RAM while full append-only log preserved. Host recomputes hash/count checkpoint incrementally; tool DB ground truth independently collected. Future raw JSONL chunks are gzip losslessly and sealed with byte SHA256, then read-only. Source snapshot is preserved perbatch.

## Next actions
1. Wait infraREADY; run final unit/live checks and paid C0/S1 smoke (fresh unique output).
2. Repair any provider integration issue without changing attacks based on outcomes.
3. Run real pilot configs/pilot.json:88runs, TTL300, real305s window,8workers,4USD total cap.
4. Validate every metric/reset/cost; set study concurrency deliberately (currently8, consider32 after resource check) and freeze sample30. Fullmanifest1200 unique cells, no doublecounting15minute sweep. Studywalltime hours; keep durable process/job monitoring.
5. Commit/push reviewed source/pilot; use testbed.freeze after required checks; commit/push/tag freeze before fullresults. Current configs/freeze.json remains blocked; do not manually claim pilot/freezecomplete.
6. Collect/analyze full real runs and tamper tests, browser-export results, numbered docs, clean synced repo/handoff.

## Resume protocol
Read this file and docs/handoff.md if present, git status, batch progress/summary and runningjobs. Preserve all raw evidence including failures. Read source snapshots for exact collection version. Never relabel scripted or engineering data as real-LLM research. Do not reset live services during collection. Never mark goal complete until actual delivery requirements met.

## Live continuation checkpoint
Real provider smoke results/provider-smoke-001 completed (legitimate task, computed token charge0.000373176USD, rawbyte hashes verified). Realpilot001 is active underexecsession79317; dashboard discoversCLIbatch read-only. At lastcheck63/88complete, zeroinfra failures. Fullstudy remains blocked. Mainserviceimage currently excludes latest duplicate-receipt audit/JITevidence/intent-multiplicity edits; DO NOTrebuilduntilpilot001finished. Afterfinish, rebuild and reruncontrols, then performfinalpilotvalidation onlatestimage beforefreeze. Currentunit48pass. Dashboard8765 PID11892/session93707.

Fullparameterdecisionbeforefull:16workers on16.98GBRAM/16logicalCPU host; observation_margin_seconds90 and cap3690 provide enoughpost-expiry follow-up forpredeclared60sexposurebar plus10sprobe resolution. Pilot001retains original305swindow. Newrunnerconfig_fingerprint normalizesfloatfields soGUI/JSONequivalentnumericvalueshashidentically. LaterrawJSONLchunksaregzip withbyteSHAseal; .gitattributes preservesresultsbytesacrossplatforms.
