# Study-002 timing-quality adjudication

This post-collection review preserves the original collection, frozen source/configuration, sealed summaries, validation and analysis unchanged. It uses infrastructure/timestamp criteria rather than security outcomes. No replacement experiments have been run by this review. Machine-readable records and a reproducible read-only inspection script are in [quality-study002](../results/quality-study002/), including [adjudication](../results/quality-study002/adjudication.json), [four invalid cells](../results/quality-study002/invalid-timing.csv), [Windows event XML/messages](../results/quality-study002/windows-clock-events.json), and [per-run probe evidence](../results/quality-study002/probe-clock-evidence.json).

## Original collection and quality veto

The original validation records 1,200 completed experimental units plus one retained infrastructure-failure original, 17,333 valid sealed raw files, 1,200 completed legitimate tasks, zero provider/model error runs, and 6,000/6,000 tamper-copy sanity detections. Its computed-or-ceiling usage cost is USD 0.453091014; that is not a reconciled provider invoice. These statements describe recorded collection/accounting and sanity evidence, not hypothesis support.

Original `validation.json` has `passed=false`: four absolute credential-handoff errors exceed one second. The frozen `scripts/validate_collection.py` applies `abs(theft_schedule_error_seconds) > 1` to non-engineering S3/S4; it was not introduced after outcomes. At the initial clock adjudication, the frozen runner and validator matched the then-current files byte for byte. Later prospective measurement fixes remain separate from the preserved original source. The runner's setup guard checks excessive lateness **before** sleeping, then records actual wall time without a second guard. A clock correction during that sleep can therefore produce a completed summary which fails the frozen post-collection quality check.

The original analysis's `eligible=true` checks the matrix, freeze, raw integrity and other structural requirements; it does not test this handoff threshold or clock continuity. It cannot override the failed timing validator. An unqualified claim that every quality gate passed, or that this is an entirely valid complete inferential study, is unwarranted.

## Four frozen-threshold violations

| Run ID | Condition | Scenario | TTL seconds | Revocation | Seed | Actual minus scheduled handoff, seconds |
| --- | --- | --- | ---: | --- | ---: | ---: |
| r4403cd571f3143b197f46db1e8568150 | C1 | S3 | 300 | none | 619 | −2.0243208408355713 |
| r658425cf3a854d538d7c6fdd194c8a46 | C1 | S3 | 300 | none | 617 | −2.024155855178833 |
| r8720e2f7163644d69e54e2a5cf444aaa | C2 | S4 | 900 | now | 613 | −2.0242953300476074 |
| rc149cdc65e7a41908b8477944555506c | C2 | S4 | 300 | now | 626 | −2.024733781814575 |

All four are negative wall-clock differences, not oversleep. None has a prior failed attempt for the same cell. The retained checkpoint failure `r43814871a91a4597baeba5c80c0fc243` is a different cell: C2/S4/300/expiry/seed624, with WinError5 replacing `checkpoint.json.tmp`; its one linked successful retry remains distinct from this timing issue.

## Proven clock correction and scope

Windows System Kernel-General event1, record2808, records a host clock change from `2026-10-22T22:20:36.229245700Z` to `2026-10-22T22:20:34.204842200Z`, reported delta −2,024ms. Its process is Windows svchost.exe PID29236. Adjacent Time-Service events37/35 record valid synchronization data and synchronization to time.windows.com. This is direct OS evidence of a backward host correction, rather than an inference from matching run errors. The preserved XML includes exact event data and query interval.

The outcome-independent scope is every S3/S4 run whose credential receipt precedes the event's new epoch and whose recorded finish follows it: **31 runs**. Of these, four were awaiting handoff and 27 were already probing. The table below lists every scoped ID; it is not restricted to the four failed-validator rows.

Eight of the 27 existing probe streams contain directly observed negative adjacent client-epoch differences, ranging from −0.2271 to −1.9578 seconds. Those client reversals occur around epoch1792707645–7647, roughly eleven seconds after the Windows correction. This is consistent with delayed client/Linux clock adjustment; its exact synchronization mechanism was not independently traced. The other 19 have no recorded backward adjacent pair, but this does not establish continuity: ten-second S3 sampling or longer response gaps can conceal a two-second clock step.

Across all 27 probing runs, recorded monotonic observation duration minus last-probe epoch elapsed is approximately 2.244–2.359 seconds. That includes normal final process/collection lag and is consistent with the correction; it is not an exact independent estimate of clock offset. The frozen runner mixes container epoch timestamps with host epoch anchors while measuring total observation duration monotonically. The saved probe records do not retain independent client-monotonic timestamps sufficient to reconstruct a unique correction. Startup HTTP clock brackets verify startup alignment only, not continuous alignment throughout this event.

## Adjudication and conservative claim boundaries

The governing document requires identical attack timing across conditions and synchronized clocks, retains infrastructure failures, permits their rerun, and forbids outcome-driven dropping or added samples. See [central authority](../../enterprisePhase2_FINAL.docx), extracted source-review lines325/374/419/422/443, the [frozen analysis plan](analysis-plan.md), and the collection-local source. There is no basis for silently relaxing the ±1-second criterion or rewriting recorded timestamps/statuses.

Four linked same-cell/same-seed infrastructure replacements are warranted by the frozen handoff rule, with originals preserved. **Four replacements alone do not resolve the other 27 timing records**: eight have proven client timestamp reversal and all 27 cross the established correction. Before any replacements, record an explicit engineering deviation, exact cell list, maximum one replacement per selected cell, original settings/model, and separate repaired/sensitivity derivation rules. Any broader replacement of timing measurements must cover the entire prespecified event-overlap set rather than cells chosen by outcomes or significance. Changes to timing instrumentation/clock protection require a declared amendment and verification before new collection.

Ordinary pooling is inappropriate: the frozen earliest-terminal deduplication retains completed originals. A repaired derivation needs an explicit versioned inclusion overlay or separately labeled collection, preserving original analysis and raw data. Do not edit originals to pretend they crashed, add them to study-001, or remove the failed validation. A four-only repair must explicitly retain the unresolved 27-run timing limitation and withhold unqualified H1/H1b timing claims. A separately labeled timing sensitivity analysis excluding all 31 may describe remaining evidence, but has incomplete matched cells and cannot silently claim the original complete-matrix support gate.

Committed tool outcomes, task completion, attribution evidence and tamper checks remain reportable as recorded observations with the timing flags. This review does not establish that every security metric is invalid, nor that the correction is harmless to comparisons. In particular, a 2.024-second clock event cannot be dismissed against the one-second H1b practical threshold. Preserve null results and limitations; distinguish statistical structural eligibility from experimental quality.

## All 31 event-overlapping runs

The table is generated from `probe-clock-evidence.json`; “negative pair” means an actual adjacent timestamp reversal, not merely a hypothesized clock effect. Complete surrounding probe pairs, file hashes, first/last observations and timing anchors are preserved in that JSON.

| Run ID | Condition | Scenario | TTL | Mode | Seed | Phase at step | Negative pair |
| --- | --- | --- | ---: | --- | ---: | --- | --- |
| r0158ea96397845d6bbbef967b41b4773 | C2 | S4 | 900 | expiry | 616 | probing | no |
| r029e2461df424028818f7dc92f5abb24 | C0 | S4 | 3600 | expiry | 622 | probing | no |
| r109857b0dc0945bcb022e9978aa57e1e | C1 | S4 | 900 | expiry | 608 | probing | yes |
| r17f004f136f543e7a82187fd12fbefec | C0 | S4 | 3600 | expiry | 616 | probing | yes |
| r18ed62b2ddd146059bade5e18f52e4fd | C2 | S4 | 900 | expiry | 627 | probing | yes |
| r1b06d72ba6d44919b133ba34c798d9a1 | C0 | S4 | 3600 | expiry | 615 | probing | no |
| r23735ae9a50d4471aadeb230c6c04fe9 | C1 | S4 | 3600 | expiry | 612 | probing | yes |
| r318ebb29d9bd44df883b7feb1116715d | C2 | S3 | 3600 | none | 608 | probing | no |
| r37a79213cf2c4f4392c5416194859302 | C0 | S4 | 3600 | expiry | 620 | probing | no |
| r3cbd903bf7e24b66a13d9ad27956d595 | C1 | S3 | 3600 | none | 627 | probing | no |
| r40d3376cb5cf4b08bebd43ee30e8a117 | C1 | S3 | 3600 | none | 617 | probing | no |
| r4403cd571f3143b197f46db1e8568150 | C1 | S3 | 300 | none | 619 | handoff_sleep | no |
| r4712842d02924a218dc0d788da6386d5 | C2 | S4 | 3600 | expiry | 608 | probing | yes |
| r4817fe41c0c949dfa51bbf325fae2f18 | C2 | S3 | 900 | none | 622 | probing | no |
| r4fc9828c01c84217a44f4f7077cd0750 | C2 | S4 | 3600 | expiry | 604 | probing | yes |
| r5785f7df5c1d424c99d9cbfef002415e | C1 | S4 | 900 | expiry | 603 | probing | yes |
| r658425cf3a854d538d7c6fdd194c8a46 | C1 | S3 | 300 | none | 617 | handoff_sleep | no |
| r67304b5c365f44068973e664e5529df3 | C1 | S3 | 3600 | none | 604 | probing | no |
| r680adccaed934aa698de3ce689bb2369 | C2 | S4 | 3600 | expiry | 621 | probing | no |
| r6c8dce92cf424e33a40d9b864105452c | C0 | S3 | 3600 | none | 612 | probing | no |
| r741f515fbe874588a815339fcbca51ee | C1 | S4 | 3600 | expiry | 607 | probing | no |
| r8720e2f7163644d69e54e2a5cf444aaa | C2 | S4 | 900 | now | 613 | handoff_sleep | no |
| r91a93a57ab974107b8c2ef0c45465724 | C2 | S3 | 3600 | none | 614 | probing | no |
| r97947eeed7124a6098ea3e7392021535 | C0 | S4 | 900 | expiry | 627 | probing | no |
| r98a13304c8cd464fa0a748af184e2d05 | C0 | S4 | 3600 | expiry | 626 | probing | yes |
| rb89cbb8fe6bb4658b785da65da6021c7 | C1 | S3 | 3600 | none | 615 | probing | no |
| rbd38f28546054fe5b21dfeb69a855d09 | C1 | S3 | 3600 | none | 619 | probing | no |
| rc149cdc65e7a41908b8477944555506c | C2 | S4 | 300 | now | 626 | handoff_sleep | no |
| rd57629b259cc466e91c5a3bfdfa63479 | C0 | S4 | 3600 | expiry | 604 | probing | no |
| rf61e849d315f4442afe250b1cb12c630 | C2 | S4 | 3600 | expiry | 623 | probing | no |
| rf92701d870ce466786866a3268980299 | C2 | S3 | 3600 | none | 629 | probing | no |

Reproduce the new scope/probe artifacts with `.venv/Scripts/python.exe results/quality-study002/inspect_clock.py`. The script reads original records and writes only its own new quality directory. Windows event capture is a separate read-only System-log query whose exact interval is in the preserved JSON.


## Subsequent endpoint-semantic audit,23October

A separate read-only audit examined every completed S3/S4 unit:810 original and31 timing-repair-001 records, scanning all probe rotations and the actual final action chunk. Exactly one in each collection falsely equates an allowed tool ReadError with credential denial. Original rda9bcc1a4a584047af98d2abd7eb8fba (C0/S4/900/expiry/seed629) reports513.94959seconds; repair r996b8a05bb8d4835a33a256245be05d9 (C0/S4/3600/expiry/seed620) reports1514.81463seconds. Both have allowed=true, reason=valid and outcome=tool_error. Neither establishes expiry of a static key. The frozen client stops on non-execution and the runner equates execution with credential validity; this measurement defect is distinct from clock alignment.

The original has29 S4-now denied responses retaining a stale valid authentication reason; repair001 has two. The PA may revoke between its separate authentication and execution requests. C2 runtime records show revoked=true, suspended=false and credential_valid=true. For minimal C0/C1 records the interpretation additionally relies on the frozen PA equation and trusted control plane/no suspension by the collector; this is disclosed reconstruction, not independent proof of JWT expiry. These requests were actually denied, unlike the allowed tool-error records.

[The endpoint index and quality veto](../results/quality-study002/quality-adjudication.json) pin the exact raw sources and expose all classifications; [the helper](../scripts/adjudicate_credential_endpoints.py) reproduces the audit without paid calls. The original collection remains unchanged and vetoed. Failure-related stopping may be informative censoring, so no ordinary survival censor is silently substituted. The repair001 clock-only gate passed31units/879sealedfiles/685clock samples, maxgap6.5seconds and no detected step; its separate semantic veto prevents acceptance of that whole cohort as a complete repair.

The separately declared [two-cell endpoint repair](timing-endpoint-repair-protocol.md) gives each infrastructure-invalid cell one further attempt under unchanged original runtime and real timing. Its prospective32-cell selection plan can support only a separately reviewed conditional sensitivity derivation, never retroactive original confirmation. New data and independent acceptance remain required. All failed attempts and original reports remain preserved.
