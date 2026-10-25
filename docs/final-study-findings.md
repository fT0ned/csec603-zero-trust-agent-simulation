# final-study-001 findings

Collection `results/final-study-001` (frozen by tag `final-study-freeze-v1`, fedd511b). Generated tables: `results/final-study-001/analysis/` (frozen analyzer `analysis/final_study.py`; wording layer `analysis/final_study_report.py`, a post-freeze presentation step that recomputes nothing). Protocol: `docs/final-study-protocol.md`. All numbers are measured in this single-machine testbed with `deepseek-flash` (one system fingerprint, 8,993 returned-model records).

## Collection
3,090 planned runs: Part A 2,100, Part B 840, Part C 150. All 3,090 cells have one completed unit. Part A had 9 infrastructure failures (HTTP 500 from PA tool reset, Docker CLI crashes under 32-way load, one tool_failure probe error), each given exactly one linked rerun that completed; originals are kept. Clock monitor: 41,925 samples, no wall-clock step over 0.5 s, max handoff error under 0.02 s, so zero flagged runs and zero timing reruns. One C3 S3 unit ended with a provider transport error (retained as a unit; it is why `validate_collection` on Part A reports one error "usage/model absent"). Raw seals verified for all parts. Cost USD 0.855 computed; ledger now 1.69 of the 4.00 cap (no budget change).

## Part A (original design, LLM agent)
- S2 and S5: the model followed the injected instruction in 0/30 runs in every condition (Wilson 95% upper bound 11.4%), so the unauthorized outcome was 0/30 everywhere. C0/C1 versus C2 contrasts in S2/S5 are null; H2b and H2c in Part A are not supported (nothing to remove or rubber-stamp). This repeats the earlier real-model "no attempt" finding.
- S3 replay: harmful replay executed in 90/90 C0 and 90/90 C1, 0/90 in C2, C2-AS, C3, C3-AS. C0 never expires (right-censored at the window, 0/90 events). C1/C2 first denial follows credential lifetime (median exposure 172/772/3472 s for TTL 300/900/3600). C2-AS, C3, C3-AS refuse the stolen bearer token at the first probe (exposure 0 s, 90/90 events).
- S4: same pattern; the operator revocation is moot for C3/AS (recorded as `revocation_moot`).
- Availability: the legitimate agent after attack is allowed 30/30 per cell in C3 and 0/30 in C2-AS and C3-AS (suspended).
- Tamper: 10,500/10,500 altered audit copies detected (sanity check). S1 benign task completion and latency: `analysis/latency-overhead-approval.md` (descriptive; runs share one host, S1 action latency medians 149/185/225 ms for C0/C1/C2, authorization median about 7 ms for C2).

## Part B (objective-driven authorization)
Every adversarial cell: C0 and C1 30/30 runs with an unauthorized commit, C2 0/30; noWF 30/30 on workflow-export; RS 30/30 on approval-payment. All 20 positive-control cells (10 original, C2-AS and C3 new) completed 30/30 with 0 false denials. A1 (8 contrasts), A2, A3: all 10 supported by the frozen rule (exact McNemar, Holm); caveat: near-deterministic repeats at temperature 0.

## Part C (LLM legitimate agent, scripted thief)
Stolen token executed 30/30 in C1 and C2 (150 records exported each condition; C2 blocked the attacker e-mail 0/30 sent), 0/30 in C2-AS, C3, C3-AS. Median first probe refusal 242 s (C1, C2) versus about 0.06-0.08 s. Containment median 2.3 ms. Legitimate agent after attack: 30/30 in C1, C2, C3; 0/30 in C2-AS and C3-AS. Legitimate task completed 30/30 in all conditions.

## Verdicts by evidence class
See `analysis/paper-package.md` and `analysis/h-verdicts.md`. Mechanism verification (counts, no p-value claims): H1, H1b, H3 (attribution of replay), H3b, B1. Measured behaviour: H2 (C0/C1 pursuing explicit objectives in Part B supports A1-A3; the S2/S5 injection route is a null), H2b/H2c in Part A null. Descriptive: H4, B2 (availability cost of auto-suspend is total in this design).
The frozen analyzer's own H1/H1b/H3/H2 table labels (e.g. "Not supported") come from its p-value judge applied to configuration-determined contrasts; the report layer re-words them as threshold counts. Read `paper-package.md`, not the raw judge labels, for those rows.

## Limits
One model alias, one host, synthetic tools, simulated approver, scripted thief, 4 S2 payloads and 6 Part B objectives (effective n below 30), Part A timing ran alone after Parts B/C (not interleaved).
