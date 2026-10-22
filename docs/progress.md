# Durable engineering progress

Updated 2026-10-22 20:26 Asia/Dubai. Read this first on continuation, then Git status and the current batch's progress, manifest and summaries.

## Authority and fixed design
Read the complete governing enterprisePhase2_FINAL.docx including its embedded diagram, all five Phase2/0Documentation sources, and docs/research-brief.md. Extracted source text/figure are outside Git in ../source-review. Official requirements and professor feedback prevail. C0 static/minimal logs, C1 real SPIRE broad/identity logs, C2 SPIRE+OPA+trusted delegation+atomic workflow+careful simulated approval/one-use120secondJIT/full audit. C2-noWF and C2-RS only S2/S5. Preserve S1–S5, real300/900/3600secondTTL, common gateway deny-list, protected ground truth/checkpoints and independent tool-state oracle. Full matrix1200unique trials,30repeats, no duplicate15minute sweep.

## Implementation and verification
- Real11service Docker topology, SPIRE1.14.1 attested UID10001 JWT-SVIDs, OPA1.10.1, separate UID10002 attacker, four private stateful synthetic tools, gateway/PA control boundaries. Dependencies and base images pinned; .venv installed.
- Latest unit suite53passed. Live source/image match, all8app services healthy/same image, allTTL signatures/audience, network/direct-IP isolation, provider-secret separation, clocks and all7control checks pass in docs/verification/final-live.json (16:23UTC). Verification namespaces retired, audits retained.
- Final engineering protocol smoke3/3passed; immediate revocation observed about116ms in this engineering check. Allrawseals/analysis pass. Engineering is never real-LLM evidence.
- Actual setup.ps1 and launch.ps1 tested. Dashboard http://127.0.0.1:8765 PID7944, execsession62493. Browser tested presets/start/progress/results/traces/CSV/JSON/SVG/ZIP/reset; latest137ZIPmemberchecksums valid, sourceCRLF bytes preserved, no provider key, tempZIP cleaned. Evidence docs/verification/dashboard*. Reset preserves raw.
- Constant-memory streamed audit/tamper verification and bounded server state; compressed1MBJSONL rotations/read-only byte seals. Source snapshot+Git/config/platform metadata perbatch. External CLI batches discovered read-only by dashboard.

## Genuine retained collections
- results/engineering-001:88scripted engineering completed, zero failures, allseals verified. Earlier code uncommitted and no collection source snapshot: diagnostic only.
- results/provider-smoke-001:1real-LLM engineering task completed,3provider requests, computed charge0.000373176USD; preserved transcripts/usage/model/fingerprint/seals.
- results/pilot-001:88real-LLM pilot runs completed, zero infrastructure/provider/model errors; all legitimate tasks complete, computed cost0.024906804USD,440/440tamper sanity detections. This uses earlier variable-theft/PArevocation protocol; keep separate diagnostic collection, not finalfreeze pilot.
- results/stress-001:33scripted S3 trials at32workers and2secondengineering windows, zero failures. Short capacity check, not sustained-memory proof; peakRAM unmeasured. Post-checkfreeRAM1.62GiB recorded.
- results/final-protocol-smoke-001:3scripted S3/S4 finalprotocol checks; zero failures, rawvalid.
- Two browser-created one-trial scripted batches plus smoke-001 retained.
- **results/pilot-002 is ACTIVE**, CLIexecsession16079, started16:23UTC. Last59/88completed, zero infrastructure failures. It uses final realLLM protocol,32workers, TTL300/305secondwindow, fixed120second receipt-to-theft handoff, concurrent isolated S3 reachability, fixed probe grid, S4 security decision after valid streaming probe. Do not rebuild/reset services while active.
- **No full-study collection yet.** configs/freeze.json remains blocked pending finalpilot validation and clean pushed source/evidence.

## Provider and budget
Ignored APIKEY_GENAI_USETHIS.txt handed off actual DeepSeek key, imported into ignored .env. Never expose/stage either. Read-only initial balance4.93USD, duringpilot0024.91USD (rounded provider balance); shared ledger computed/ceiling spend about0.047USD at16:25UTC, allsettled. This difference is not an exact per-batch invoice. Conservative aggregate STUDY_BUDGET_USD=4; no topup. Preserve .runtime/spend.sqlite, including uncertain reservations; never reset it. Model deepseek-flash is a mutable alias officially documented DeepSeek-V4.1-Flash-1017; preserve actual responses/fingerprints/usage/catalogue/cost labels. No fallback. Official pricing/API/privacy sources checked. Hosted GitHub secret scanning could not be verified (APIsecurity_and_analysis:null); local exact-secret scans required before each push.

## Parameters resolved before full
Full/finalpilot32workers chosen after short capacity check; sample30default, not outcome-tuned. Fullmaxwindow3690/TTL+90second margin protects predeclared60second practical exposure criterion plus10second sampling. S3interval10seconds; S4.1seconds. Handoff120seconds from observed credential receipt, actual schedule error retained and >1second misses become infrastructure failures. Windows runner holds a temporary idle-sleep prevention request; manual sleep/lid closure can interrupt. Do not shorten real observation or substitute scripted runs.

## Next actions
1. Await pilot002 completion, inspect ALL units/cells, timing, errors, raw seals, independent tool-state evidence, audit/tamper coverage, legitimate completion, cost and uncertain reservations. Run scripts.validate_collection and analysis.cli --verify-raw. Do not tune attacks from pilot outcomes.
2. Finish architecturefigure QA and copy browser evidence; update numberedrunbook. Commit/push final source, configs/plans, verification and all finished raw collections after exact-secret scan. Never stage active raw files. Source snapshots preserve each earlier protocol; analysis partitions by collection.
3. With clean syncedtree, run testbed.freeze --pilot results/pilot-002 --study configs/study.json. It validates finaltiming/concurrency, allplannedcells, sealedraw, actualLLM usage/model/cost, tamper/oracle/timing and budget projection. Commit/push approvedfreeze and create/push immutable study-freeze-v1 tag BEFORE full collection. Do not manually approve JSON.
4. Run testbed.cli with configs/study.json to results/study-001;1200genuineLLM units, realTTL windows,32workers, hours. Preserve original infrastructure failures with one same-seed rerun; model/provider errors stay experimental units. Do not change frozen core/config/analysisplan or restartcontainers during collection. Monitor durableprogress and spending.
5. Verify/analyze full, browser complete workflow/export checks, uncertainty/hypothesis assessment, paper-ready artifacts, final docs/handoff.md, clean syncedrepo. Actual user objective remains unfinished until these verified deliverables exist.

## Resume protocol
Check current processes before launching another batch. Preserve all failures/raw/seals/source/ledger. Source edits are shared across agents; coordinate ownership. Agentdashboard completedQA; infracompletedfinalverification; analysisagentfinishingarchitecturefigure. No agent has commit permission assigned; lead commits integrated work. Existing goaltool reports usageLimited from earlier accountpause; user resumed and tools work. Do not mark complete while any required work remains. Never fabricate or relabel diagnostic/scripted evidence as fullreal findings.
