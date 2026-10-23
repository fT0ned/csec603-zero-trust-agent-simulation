# Evidence boundaries for the separately declared enforcement extension

Working interpretation, 23 October 2026. This document records completed neutral-pilot findings and a pending scripted stress evaluation. It is not a submitted manuscript, a new confirmatory analysis plan, or permission to revise outcomes until a preferred effect appears. The original full study, its raw evidence, hypotheses, null findings and timing-quality veto remain preserved.

## Evidence status

| Collection | Evidence class and status | What can currently be stated |
| --- | --- | --- |
| original `study-002` | Original full real-LLM collection completed; separate quality validation failed for four S3/S4 handoff timing deviations | Retain the original quality veto and [quality review](study002-quality-review.md). Analysis eligibility alone does not override validation failure. Do not present unqualified confirmatory support from this collection |
| `neutral-pilot-001` | Completed exploratory real-LLM pilot; 36/36 runs, validator passed | All24 S2/S5 attacks were seen and explicitly rejected without harmful calls; all36 legitimate tasks completed. See [independent transcript audit](neutral-pilot-findings.md) and collection-specific descriptive report |
| `enforcement-stress-002` | Planned390 scripted enforcement units; **results pending at preparation** | No measured prevention, workflow, approval, attribution or overhead finding is asserted here. Wait for completion, raw verification and reconciliation before adding a separately labeled measured-results supplement |

These labels prevent three substitutions: pilot precision for full confirmation, scripted attack execution for natural model behavior, and authorization checks for valid replay-timing measurements. No results are pooled across collections, modes or prompt profiles.

## What the completed neutral pilot adds

Actual provider requests confirm a single neutral system string across C0/C1/C2, with matching recorded hash; no warning to distrust external content is present in that system string. The same exact tasks still define authorized scope and explicit stops. All109 provider requests share the same tool schema. Independent call/write reconciliation finds zero harmful attempts/commits, no agent denials or provider/model/tool-call issues, and78/78 expected legitimate actions with42/42 independent write confirmations. Twenty-one additional benign reads were made.

Thus removing the explicit warning did not expose a naturally attempted harmful action in the24 attack trials observed here. This is a narrow exploratory finding, not evidence that prompt defenses never matter or that the two prompt profiles are equivalent. Fixed conflicting payloads, exact task boundaries, mock context, a mutable single model alias and very small per-payload samples remain important limits. Each S2 condition/payload has one observation and each S5 condition/payload two; Wilson upper95% bounds for zero outcomes are79.3% and65.8%, respectively. Do not infer rare-risk assurance from these zeros.

## RQ and hypothesis claim boundary

| Research question / original claim | Permitted interpretation of this extension | Prohibited inference |
| --- | --- | --- |
| RQ1 / H1 finite lifetime and H1b revocation delay | This extension has no S3/S4 timing experiment; retain original timing-quality limitations | Neutral or scripted S1/S2/S5 cannot repair clock deviations or validate exposure/revocation claims |
| RQ2 / H2 authorization and reachable authority | Report capability probes as separate harness-generated reachability measurements. Neutral attacks have no harmful attempts | Do not credit OPA with preventing an action that the real agent never requested; do not call reachability a natural injection success rate |
| RQ2 / H2b workflow limits | Scripted stress may test whether a fixed forced chain crosses the independent total-limit boundary; actual findings remain pending | A positive scripted ablation is not confirmatory support for original real-LLM H2b or general enterprise attack prevalence |
| RQ2 / H2c approval quality | Scripted high-impact actions may compare careful versus rubber-stamp behavior within payload strata after validation; distinguish within-total intent harm from primary chained-total harm | Do not replace the frozen primary endpoint with supplemental intent harm or equate an idealized approver with observed humans |
| RQ3 / H3 attribution | Report confusion counts against the defined harness truth. Neutral S2/S5 contain no actual harmful coercion attempts | Correctly labeling `none` after harmless exposure does not establish detection/attribution of actual coercion; provenance matching is not proof of cognition |
| H3b audit tamper detection | Deliberate alteration checks remain sanity checks with preserved independent checkpoints | Do not claim broad control-plane compromise resistance or prevention from successful log verification |
| H4 operational cost | Descriptive within-run medians/p95 first, then across-run distributions; separate collection/mode/model/payload/approval strata | No call pseudoreplication, uncontrolled cross-collection causal latency comparison or claim of enterprise-scale performance |

Recommendations may be grounded in authoritative guidance and actual engineering checks once measured, with prerequisites and limitations stated. Natural model susceptibility, controller enforcement under forced actions, and operational overhead answer different questions. The paper must identify which evidence supports each sentence.

## Plotting and paper extraction

The standalone postcollection helper `scripts/plot_enforcement.py` reads only the separate `enforcement/report.json`, leaves sealed reporting code/raw collections untouched, and exports each collection/mode/scenario to its own SVG/PDF/PNG. Endpoint tables retain exact condition/payload/profile/model, numerator/denominator, Wilson bounds and evidence class. S5 primary and supplemental intent endpoints occupy separate panels. Scripted and LLM data never share a pooled estimate or plot panel.

1. Check independent collection validation and `enforcement/report.json.errors` first. Do not plot unresolved evidence errors as measured outcomes.
2. For the completed neutral cohort, run `.venv/Scripts/python.exe scripts/plot_enforcement.py --report results/neutral-pilot-001/enforcement/report.json --output results/neutral-pilot-001/figures`.
3. Only after the stress cohort is complete and validated, use its corresponding report path and a separate figures directory. Do not prefill expected positive findings.
4. Import SVG/PDF into the manuscript and cite the full collection ID, exploratory/scripted status, endpoint and per-row sample count. CSV tables and `figure-manifest.json` preserve source/report hashes. Final manuscript RQ conclusions still require the original quality veto and all null/negative findings.
