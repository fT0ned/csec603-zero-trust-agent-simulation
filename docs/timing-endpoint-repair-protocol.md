# Separately declared endpoint repair and conditional sensitivity

Declared before timing-repair-002 data collection. The original study and timing-repair-001 remain immutable and quality-vetoed; a wrapper clock pass does not override a semantic veto.

The read-only audit examined all810 completed original S3/S4 units and all31 repair units, including all rotated probes and each terminal action. Exactly one original and one repair endpoint were allowed tool ReadErrors rather than access denials. Original rda9bcc1a4a584047af98d2abd7eb8fba (C0/S4/900/expiry/seed629) and repair r996b8a05bb8d4835a33a256245be05d9 (C0/S4/3600/expiry/seed620) retain their recorded false events. These observations are competing tool failures, not evidence that a non-expiring key expired. Failure-related censoring may be informative; no ordinary survival censor is silently substituted.

Twenty-nine original and two repair S4-now denials retain a stale valid authentication reason. The PA can revoke between credential validation and execution. These are denied requests, not allowed tool failures. C2 runtime signals explicitly show revoked=true and suspended=false. Minimal C0/C1 logs require the frozen PA equation, declared revocation and trusted-control-plane assumption; this is a bounded reconstruction, not an independently observed JWT expiry. Exact records, raw hashes and classifications remain inspectable in the separate endpoint audit.

## Two new attempts

The exact two original cells and hashes are in results/timing-repair-002/repair-protocol.json. Each receives one new attempt, no retries. The second is a linked replacement for the invalid repair001 attempt as well as its original clock-overlap cell. The original frozen study-freeze-v2 runtime, image, model, prompt, tasks, controls, seeds, lifetimes,120-second handoff and original probe/window settings remain unchanged. Two actual workers replace the prior31/32-worker dispatch; this contention difference is a sensitivity limitation. The shared4USD ledger remains authoritative. No service rebuild, reset, clock reconfiguration, model search or security-control change occurs.

The copied wrapper retains the previous clock/raw/handoff gates and adds a frozen endpoint-helper veto: a terminal tool/infrastructure failure cannot pass as credential rejection. Both attempts must complete and pass all gates, including semantic review. Any failure remains preserved and this finite one-attempt cohort is not automatically extended. Clock sampling still cannot prove perfect continuity between readings. C0 is non-expiring, so expiry-mode C0 should remain observed-valid through the actual window; this expectation is not a criterion for selecting favorable security outcomes.

1. Inspect the protocol, two cells, endpoint review, hashes and selection plan. Preparation-only: `.venv/Scripts/python.exe results/timing-repair-002/collect_repair.py`.
2. After the pushed precollection tag timing-endpoint-repair-v1 and idle-service check, run the same command with `--execute`. Existing started/runs paths cause refusal. Longest duration is about65minutes of actual wall time.
3. Preserve all raw, clock, endpoint-review and quality records. Original failed quality records are never overwritten. Do not rebuild or run concurrent experiment/verification traffic while collecting.

## Prospective derived selection

results/timing-sensitivity-001/selection-plan.json fixes1168 original units,30 individually reviewed unaffected repair001 units and two new repair002 units. It excludes the full31-clock-overlap original set and the separate original tool-failure cell. Security effects and significance play no selection role. The full repair001 cohort remains vetoed even if30 unaffected units are usable in this separately declared derivation.

No accepted view is created before new data and independent quality review. A hash-bound acceptance must verify every selected unit's raw bytes, exact cell correspondence, endpoint semantics and applicable clock criteria. A portable1200-row ledger identifies every source collection/run/hash; an ignored transient junction view permits the unchanged frozen analyzer to run without copying or modifying raw records. Report original and conditional amended estimates/intervals side by side. Structural eligibility and frozen hypothesis labels do not retroactively validate the original experiment. Mutable model alias, later collection, worker counts, sampled clocks and reconstructed stale-reason attribution remain limitations.
