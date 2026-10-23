# Durable progress — 23 October 2026

## Current state and user-directed extension

Original `results/study-002` FINISHED: 1200 completed units, one retained checkpoint infrastructure failure with one successful linked rerun. No original collector remains active; dashboard is http://127.0.0.1:8765. Do not restart the original batch or edit frozen evidence. Tag study-freeze-v2 / 4ddfbe4 remains immutable.

Validation FAILED four handoff timing checks. Windows logs prove a backward 2024ms clock correction; 31 replay/revocation runs overlap it (four sleeping,27 probing). Eight probe streams show backward timestamps. See docs/study002-quality-review.md and results/quality-study002. Structural analysis eligible=true does NOT override this veto. Preserve original analysis and failed validation. No replacements collected; unqualified timing inference is withheld. A later timing repair would require a declared outcome-independent31-cell protocol, linked replacements, and separate inclusion overlay.

Raw integrity passed17333 sealed files;1200 legitimate tasks completed;6000/6000 tamper sanity checks;0 provider/model errors; successful-run cost/ceiling0.453091014USD. Shared aggregate ledger0.526116414USD/4425requests, no pending, balance4.41USD at08:21UTC23Oct. Preserve .runtime/spend.sqlite and established4USD cap.

All340 original pilot/full S2/S5 transcripts were audited: payload verified in model requests340/340, explicit rejection340/340, harmful calls/commits0. No missing payload or broken tool loop. Legitimate expected actions and independent writes reconcile. Separate diagnosis: docs/diagnosis-original-agent.md and results/diagnosis-original. These results do not exercise gateway prevention of malicious agent actions.

User explicitly requests a Zero Trust enforcement focus: same fixtures/tasks across conditions, neutral shared system prompt, separate real-LLM exploratory pilot and deliberately malicious scripted stress test. Original source/config/raw/analysis/tags remain unchanged. New protocol/config/version must identify prompt change, exploratory status, identical controls, and scripted provenance. No favorable-outcome tuning, silent pooling or scripted substitution for LLM evidence. Use same shared ledger. Optional models only if warranted/access verified.

Next: commit original evidence/audits; implement new prompt selection with original default preserved; freeze separate exploratory/stress protocols before runs; test legitimate action executability; run neutral pilot and scripted stress in distinct directories; analyze actual attempts/denials/effects/approval/workflow/reachability/attribution/overhead with uncertainty. Complete browser/export QA and handoff, then clean synced Git. GitHub hosted secret scanning remains externally unavailable as documented; local exact-secret scan is not a substitute.

Subagents: infra verifies legitimate authorized action executability in isolated namespaces; dashboard checks complete-study browser/exports without frozen changes; analysis diagnosis finished. No containers rebuilt/reset. Existing services run frozenv2 image.

## Earlier operational record (historical; active status below is superseded)

# Durable progress — read before continuing

Updated 2026-10-23 00:50 Asia/Dubai.

**Final full collection `results/study-002` is ACTIVE. Do not launch another batch, restart/reset/build containers, or change frozen code/configuration/analysis/dashboard/scripts.**

## Current process and freeze

- Command: `powershell -ExecutionPolicy Bypass -File scripts/collect_study.ps1 -Output results/study-002`.
- Tool session **70824**, actual Python PID **30476**. Starts around00:49Dubai/20:49UTC22Oct. The CLI holds a temporary Windows idle-sleep request; manual sleep/lid closure can still interrupt.
- 1200 genuine `llm/full` units,32workers. At first check32running/0completed; read `progress.json` and `.runtime/study002-monitor.json` for fresh status. Lightweight operator command: `.venv/Scripts/python.exe .runtime/monitor_study.py` (mtime/size cache; reads new summaries once, no model/Docker calls).
- Wrapper automatically runs raw verification, analysis, consistency validation and read-only provider balance after collection, retaining `pipeline-status.json`. It does not perform final interpretation/browserQA/commit.
- Commit **4ddfbe4a73922fcde360b3d68bd0d104cb3b0d70**, pushed annotated tag **study-freeze-v2**. Reviewed source/evidence commit1ff36f7dd0543c5a5c338d503f58cc13b9342a59. Both commits pushed and working tree clean before launch. Results/progress make it dirty during collection.
- Approved freeze copied to batch/freeze.json and predates manifest. It binds experiment, analysis, config, dashboard, scripts, topology and locked dependencies, plus analysis-plan hash. Frozen text hashes normalize universal newlines; raw and collection-source hashes preserve exact bytes.
- Dashboard [http://127.0.0.1:8765](http://127.0.0.1:8765), PID **28496**, tool session **78282**. Browser left on completed pilot. Compact cached monitoring is active; avoid large exports/heavy jobs during collection.

## Authority and fixed design

The complete governing enterprisePhase2_FINAL.docx including its diagram, all five Phase2/0Documentation sources and docs/research-brief.md were read. Extracted source text/figure are outside Git at ../source-review. Official requirements and professor feedback prevail.

C0 static/minimal logs; C1 genuine SPIRE JWT-SVID/broad/identity logs; C2 SPIRE+OPA+trusted delegation+atomic workflow+careful simulated approval+one-use120sJIT/full audit. C2-noWF/C2-RS only S2/S5. All S1–S5, separate attacker, private synthetic tools, common gateway deny-list, protected ground truth/checkpoints and independent committed-tool-state oracle.

Frozen:30repeats,1200unique cells,no double-counted15minute sweep; real300/900/3600secondlifetimes forS3/S4; other scenarios900; seed603;32workers;120secondreceipt-to-thefthandoff; S3interval10seconds/S4.1seconds; TTL+90secondobservation/max3690. No outcome tuning, optional stopping, time acceleration or scripted substitution. Analysis keeps collection/model/phase/scenario/TTL/revocation/approval strata separate, uses run units, uncertainty/censoring/Holm and practical thresholds.

## Preserved infrastructure interruption and version history

`study-freeze-v1`/d68c527 and `results/study-001` are immutable retained originals. Study001 was stopped for an operator/monitoring infrastructure correction after **50completed/32unfinished** units;1118planned units never started. Repeated dashboard parsing of large latency arrays was identified by code inspection; the compact cache was activated before final collection to keep one monitoring implementation throughout. No security-outcome-based stopping/tuning occurred.

All82original summaries/raw fragments/source remain unchanged. Completed records retain seals; unfinished summaries remain as originally written, not fabricated into completed results. interruption.json explains the cause; partial-archive-manifest.json hashes exact archived bytes. Old client process tree/orphan clients stopped and unfinished task namespaces retired without containerreset. Full001 is incomplete and cannot support full-study hypotheses; never pool it into study002. The restart/additional attempts must be reported as a protocol deviation. Newfreezev2 records the correction before finalstudy002, using the same model/payload/policy/seed/timing/sample/inference design. See docs/pre-run-review.md.

## Completed, tested and pushed

- Real11service Docker topology, SPIRE1.14.1/OPA1.10.1, UID10001 attested caller/UID10002 attacker, four private stateful synthetic tools, actual gateway/PA boundaries, pinned images/transitive lock. setup.ps1 and launch.ps1 tested.
- **56unit tests pass**, seven focused dashboard tests. Fresh post-rebuild live source/image/health/signature/audience/allTTL/isolation/clocks and all7control checks pass; verification namespaces retired.23runtime/topology/dependency files still match finalpilot bytes. Only host freeze checker/presentation/monitor support changed afterward and is bound byv2.
- Actual pilot browser start/progress/comparison/traces/CSV/JSON/SVG/ZIP/reset verified. Finalpilot ZIP1318checksums valid,47/47collectedsources byte-exact includingDockerfile/configJSON, editableMermaid/p95CSV present,352gzipmembers decoded/secret-scanned,1243raw/sourcefiles unchanged,tempZIP0. Evidence docs/verification/dashboard-pilot-002-browser.json/.jpg.
- Monitoring correction: compact cache keyedpath+mtime_ns+size retains UI scalars/run-median latency; complete arrays remain in full exports/trace.7tests plus actual read-only API/browser checks: study00182compactrows38,784bytes, pilot88rows44,315bytes,cachedhistory0.272s,273checked files unchanged. UI compares median of run medians. Evidence screenshot docs/verification/dashboard-monitoring.jpg.
- Final analysis includes explicit model/date/approval-subgroup tables, run median/IQR/p95 and per-run call-p95 latency/authorization CSV, without changing median inference/Holm.22analysis tests; all12pilotanalysisfiles reproduce byte-for-byte in a separate directory.
- Standalone architectureSVG/editableMermaid and physical-path explanation;16-entry literature matrix;32-reference primary-source verification register;20-item feedback response matrix. Some inaccessible primary full texts remain explicitly unverified; exact Overleaf manuscript locations/integration remain a separate step, not falsely completed. See docs/reference-verification.md and feedback-response-matrix.md.
- Git results byte-preservation rule follows language rules; captured source hashes checked. Known-local staged secret scans passed before every push. Do not run whitespace checks on immutable CRLF raw files; check source with cr-at-eol and exclude results. Never alter sealed bytes for cosmetic whitespace.

## Genuine retained collections

- **pilot-002**:88real-LLM pilot,all88legit tasks complete,zeroinfra/provider/modelerrors,1108rawfiles valid,440/440tamper sanity detections,maxrecordedhandofferror0.0014484s,cost0.0246822USD,0uncertainreservations. Model followed0/20S2 and0/20S5 injections:limits enforcement interpretation; pilot descriptive only.
- pilot-001:earlier88real-LLM pilot,zeroerrors,alllegitcomplete,cost0.024906804USD,oldervariabletheft/PArevocation protocol; diagnostic separate collection, not freeze pilot.
- provider-smoke-001:1paidreal-LLM engineering task/3requests/cost0.000373176USD.
- engineering-001:88scripted engineering/0fail/rawverified; earlysourceuncommitted/nosnapshot, diagnostic.
- stress-001:33scriptedS3/32workers/2secondwindows/0fail,429rawfilesverified. Shortcapacitycheck, not sustained-memoryproof; peakRAM unmeasured, post-checkfree1.62GiB.
- final-protocol-smoke-001:3scriptedS3/S4/0fail/rawvalid; observed immediate revocation about116ms in engineering check.
- Two one-trial browser batches and smoke-001 retained. All finished earlier collections/source/raw and interruptedstudy001 pushed. No full completed study yet.

## Provider, budget and external requirement blocker

Ignored APIKEY_GENAI_USETHIS.txt handed off the actual DeepSeek key, imported to ignored.env. NEVER stage/expose either. Preserve .runtime/spend.sqlite: conservative4USDaggregate cap across batches, atomic reservations and retained uncertain ceilings, no topup/fallback. Immediately before finalstudy002, rounded balance4.86USD; settled ledger0.072737004USD, no pending. Freezev2 remaining aggregate3.927262996USD; projected1200cost with50%reserve0.5048632USD. During active requests reserved values are expected; never reset ledger to bypass cap.

Model deepseek-flash is a mutable alias officially documented DeepSeek-V4.1-Flash-1017,temperature0/thinkingdisabled. Preserve actual returned identifiers/fingerprints/catalogue/usage/transcripts/cost labels. Immutable model reproduction is unavailable. Official API/pricing/privacy primary sources checked. Computed costs/ceilings and rounded balances are not exact invoices.

**Required GitHub secret scanning is confirmed disabled/unavailable** in the specified private user-owned repository. Administrator API/settings checked; no enable control. Exact evidence/unblock steps: docs/verification/github-secret-scanning.md/.json. Needs eligible existing-entitlement organization/enterprise hosting with separately authorized ownership/access change or owner licensing decision. No purchase, upgrade, visibility or ownership change made. Local staged scanner does not satisfy that hosted feature. Keep explicit in final handoff.

## Next actions

1. Monitor session70824/progress/mtime-cached operator status and budget. Do not change ANY frozen files, run another batch, restart containers, or perform CPU-heavy export/tests during collection. All subagents completed current edits; future work only unfrozen docs, excluding analysis-plan.
2. Materialize final simulation-design and RQ→H→scenario→metric tables in docs, as identified by docs/verification/documentation-audit.md. Existing required artifacts have clear source mappings. No invented measured cells.
3. When wrapper finishes, inspect pipeline-status (PowerShell UTF8 may have BOM), batch-status, validation and actual summaries. Verify1200planned terminal units, originalinfra/reruns/provider/model failures, censoring/timing/clock/audit/tamper/oracle/cost. Reproduce unchanged frozen analysis byte-for-byte. Report actual supported/unsupported hypotheses and uncertainty, model refusals, protocol deviation and limits.
4. Full-batch browser progress/results/comparison/traces/CSV/JSON/SVG/ZIP QA; check hashes/providersecrets/source fidelity/rawunchanged/tempcleanup. Large ZIPs can take minutes; browser automation event timeout alone is not proof of failed artifact.
5. Finish measured paper-ready findings/RQs/tenartifact mappings/recommendation matrix. Preserve exact manuscript integration/access boundaries and unverified references. Write docs/handoff.md withURL,launch commands,results/reproduce steps,commits/blockers. Commit/push finalresults/docs after staged scan; verify clean synced repo. Do not declare objective complete before actual verification/handoff.

## Resume protocol

Read this file, Gitstatus/log, currentmanifest/progress/batch/pipeline-status and process inventory BEFORE acting. Sessions survive context/quota interruptions. Never restart collection merely because this chat paused. Preserve all originals/failures/raw/seals/source/ledger. Existing goal tool previously reported usageLimited from accountpause; user resumed and tools work. Never fabricate, relabel diagnostic/scripted observations, or hide an interrupted collection. Do not move either freeze tag.
