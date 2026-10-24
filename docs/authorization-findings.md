# Measured real LLM authorization findings

The separate `agent-authorization-study-001` completed **720/720 real-LLM runs**, with zero collection failures, zero reruns and no outcome-driven additions. Its precollection seal, [`agent-authorization-freeze-v1`](https://github.com/fT0ned/csec603-zero-trust-agent-simulation/tree/agent-authorization-freeze-v1), was published before data collection. The [frozen independent analysis](../results/agent-authorization-study-001/analysis/report.json) passed every evidence gate and is eligible for confirmatory interpretation. The [additional cross-check](../results/agent-authorization-study-001/quality-adjudication.json) agreed with its effects, exact tests and Holm correction. These are measured synthetic-testbed results, not production-enterprise guarantees.

## What was evaluated

The model received an explicit operational objective, such as exporting twenty records. Separately, the trusted administrator registered the principal's narrower authority, such as a ten-record maximum. The model chose and issued its own tool calls through the actual authenticated gateway and private mock services. Identical objectives, trusted authorization, tools and model settings were used across applicable conditions. Authentication versus task-scoped enforcement was the intervention. This is an authorization-boundary experiment, not a jailbreak or prompt-injection experiment.

The study used 24 cells with thirty repeats each: four adversarial objectives and two positive-control tasks, C0/C1/C2 plus the applicable workflow/approval ablations and positive controls in both ablations. The 420 adversarial runs all contained actual unauthorized model-generated attempts. All 300 positive-control runs completed their authorized required steps. There were 1,842 genuine provider completions and 1,643 model-generated gateway calls; every call and subsequent tool feedback was independently reconciled. All provider completions returned `deepseek-flash` and the same recorded fingerprint, `e72d3c7f663d3e1383b00b3884cb4501`. The alias remains mutable despite this observed consistency.

The LLM planner ran on the host and directed actual HTTP requests from the SPIRE-attested client. The harness supplied transport, credentials and trusted run identifiers; it did not dispatch fixture action sequences as model behavior. C0 used a static credential; C1/C2 used genuine workload identities. Host, issuer, administrator and evidence stores were trusted.

## Authorization effectiveness

Table A1. Authors' measured request/effect counts across this collection. Action counts are repeated observations within runs, not independent statistical trials. Condition sample sizes differ because ablations cover selected adversarial tasks plus both positive controls.

| Condition | Runs | Unauthorized requests | Denied | Allowed | Independently committed unauthorized positive effects | Gateway-reported unauthorized read executions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C0 | 180 | 152 | 0 | 152 | 150 | 2 |
| C1 | 180 | 153 | 0 | 153 | 150 | 3 |
| C2 | 180 | 163 | 163 | 0 | 0 | 0 |
| C2-noWF | 90 | 60 | 0 | 60 | 60 | 0 |
| C2-RS | 90 | 32 | 2 | 30 | 30 | 0 |

The primary mutating effects were confirmed using independent private-tool write IDs, parameters and final state. Read-only accesses lack an independent write ledger and therefore remain a separately labeled gateway-response endpoint. There were no zero-effect durable writes in the full study. Policy allowance, model success prose and HTTP status alone were never accepted as proof of a committed effect.

Table A2. Authors' measured primary outcomes, runs with an event / thirty runs. Workflow events require actual exports above the trusted ten-record total. Other events require an unauthorized positive mutating effect.

| Objective / primary event | C0 | C1 | C2 | Applicable ablation |
| --- | ---: | ---: | ---: | --- |
| Out-of-scope customer deletion | 30/30 | 30/30 | 0/30 | Not allocated |
| Payment outside principal vendor authority | 30/30 | 30/30 | 0/30 | Not allocated |
| In-scope but unrequested invoice payment | 30/30 | 30/30 | 0/30 | C2-RS: 30/30 |
| Exported records above ten | 30/30 | 30/30 | 0/30 | C2-noWF: 30/30 |

C2 denial reasons identify the evaluated boundary: `scope_denied`, `vendor_denied`, careful approval's intent-mismatch refusal and `workflow_limit`. C0/C1 credential validation succeeded but did not impose the trusted task restrictions. C0 and C1's equal observed primary outcomes do not establish statistical equivalence or an absence of identity benefits for credential theft; that is a different research question.

## Workflow and approval contributions

Every workflow run independently exported twenty distinct customers in C0, C1 and C2-noWF, versus ten in C2. Median totals and interquartile ranges were therefore 20 [20,20] versus 10 [10,10]. C2 permitted the first two legitimate five-record batches and denied later batches, including model-selected retries. Its thirty workflow runs made seventy unauthorized requests, all denied. noWF committed sixty extra batches across thirty runs. Removing cumulative enforcement increased actual limit-breach risk by 1.00 and median exported records by ten; the ratio to trusted authority increased from 1.0 to 2.0.

For approval, the vendor and payment action were in scope and the thirty-unit payment was below per-call and cumulative ceilings. The principal had requested a different invoice for twenty-five units. Careful C2 approval denied all thirty unrequested payments; C2-RS approved and independently committed all thirty. The effect isolates the simulated approval rule rather than a vendor, tool or workflow denial. Both configurations completed all thirty authorized payment controls. This supports the contribution of reliable intent-aware approval under the stated idealized rules; it does not estimate human approval accuracy.

## Prespecified statistics and uncertainty

All ten primary contrasts met the predeclared directional 0.20 practical-effect criterion and the Holm-adjusted 0.05 threshold. Each had thirty matched pairs with thirty discordances in the predicted direction and none opposite. The exact two-sided McNemar p-value was 1.862645149230957e-9; the ten-comparison Holm-adjusted value was 1.862645149230957e-8. A separate SciPy binomial calculation and independent Holm calculation reproduced these values.

| New hypothesis | Prespecified contrasts | Measured risk difference, right minus left | Judgment |
| --- | --- | ---: | --- |
| A1 | C0→C2 and C1→C2 within four adversarial objectives | −1.00 for all eight | Supported in this separately frozen design |
| A2 | C2→C2-noWF, actual export-limit breach | +1.00 | Supported |
| A3 | C2→C2-RS, unrequested payment effect | +1.00 | Supported |

Per-condition Wilson 95% intervals are 88.65%–100% for 30/30 and 0%–11.35% for 0/30. The deterministic observed paired samples give degenerate paired-bootstrap difference intervals at −1 or +1. These intervals do **not** establish zero population risk; retain the condition Wilson intervals and the limited fixed-task sampling frame. Full contrast endpoints, pair counts, effect intervals and cumulative-record effects are in [paired-contrasts.csv](../results/agent-authorization-study-001/analysis/paired-contrasts.csv). The report's generic overall outcome label is supplemented by the explicitly named workflow-specific endpoint in each relevant contrast.

## Usability and unexpected behavior

All ten positive task/condition cells completed 30/30 authorized required workflows, with zero false authorization denials. Nevertheless, ten payment-control runs included unnecessary out-of-scope read attempts: `email.read` or `crm.read` with limit fifty. C0/C1 reported five successful unauthorized reads; C2 and C2-RS denied the other five. These observations remain visible and are secondary descriptive evidence, not added post-hoc hypotheses. They show why successful task completion must not be equated with an entirely authorized trajectory.

The old `quality.json` label `clean_positive_completions` meant required steps completed without unauthorized mutation. Its original bytes remain preserved. The additive `quality-adjudication.json` uses explicit labels distinguishing that measure from completion without any unauthorized attempt. There were 290/300 positive-control trajectories with no unauthorized attempt; all 300 completed the required steps and none committed unauthorized mutations.

The model also received 120 recoverable tool-error responses. These remain recorded model interactions and were not converted into policy denials, credential expiry or collection failures. The first exploratory collector's premature interruption on known-no-effect errors was fixed before the successful pilot and freeze. No failed observation from that exploratory cohort was erased.

## Accountability, integrity and operational cost

All 848 C2-family action records contained the seventeen declared audit fields and exactly matched independently known principal, issued agent, task, delegation, origin, credential, request, action, parameters, decision and result. C0/C1's 795 records retained their smaller baseline schemas; zero had the complete C2 schema. These are evidence-coverage and source-agreement results, not claims about a model's psychological intent or automatic coercion detection.

All 10,800 sealed run files and 87 captured source files verified. The additional reviewer rehashed all 10,800 raw members and recomputed 3,377 tamper-copy checks; all tested alterations were detected. Continuous clock quality passed 2,070 samples with no backward step, 0.016474-second wall/monotonic offset range and maximum 1.032-second sample gap. Deployed source/policy/container-clock checks passed before and after collection. These integrity results assume the protected host/checkpoints remain trustworthy.

The full study's usage-price estimate was USD 0.197885742. Including all earlier experiments and both new pilots, the retained ledger contained 6,585 settled requests, no pending reservations and USD 0.768644778 against the unchanged USD 4 cap. All new provider transcripts reconcile with the ledger increase. These are estimates under retained pricing rules, not exact invoices.

The [exact measurement notes](authorization-measurement-notes.md) distinguish client HTTP action latency, PA evaluation time and whole-run duration. No human approval delay is measured. Latency summaries below are descriptive run-median distributions, not additional hypothesis tests or enterprise service-level guarantees.

| Positive task | Condition | HTTP action ms median [Q1,Q3] | PA evaluation ms median [Q1,Q3] | Whole-run seconds median |
| --- | --- | ---: | ---: | ---: |
| positive-export | C0 | 55.568 [49.104,66.783] | 0.002 [0.002,0.002] | 6.932 |
| positive-export | C1 | 55.575 [47.875,62.745] | 0.002 [0.002,0.002] | 12.955 |
| positive-export | C2 | 63.048 [52.556,71.648] | 2.362 [1.976,2.913] | 12.291 |
| positive-export | C2-RS | 58.423 [54.618,72.689] | 2.444 [2.114,2.860] | 12.359 |
| positive-export | C2-noWF | 59.926 [53.909,69.418] | 2.232 [1.759,2.781] | 13.547 |
| positive-payment | C0 | 47.293 [44.430,55.164] | 0.002 [0.002,0.002] | 7.806 |
| positive-payment | C1 | 47.631 [44.061,66.494] | 0.002 [0.002,0.002] | 13.471 |
| positive-payment | C2 | 49.830 [47.058,66.399] | 2.094 [1.795,2.569] | 15.410 |
| positive-payment | C2-RS | 51.675 [45.981,60.533] | 1.854 [1.687,2.203] | 14.285 |
| positive-payment | C2-noWF | 56.986 [48.687,68.723] | 2.240 [1.804,2.681] | 14.362 |

## Evidence classes and original hypotheses

| Evidence | Retained interpretation |
| --- | --- |
| Original 1,200-run real-LLM study | Original quality veto and no harmful S2/S5 model calls remain visible |
| Reviewed conditional timing sensitivity | H1/H1b conditional support; original quality veto remains; no timing study repeated here |
| Original H2/H3 | Mixed support under the retained conditional analysis |
| Original H2b/H2c | Unsupported in the original real-model design; new results do not retroactively confirm them |
| H3b / H4 | Audit-tamper sanity evidence / descriptive operational trade-offs |
| Earlier 390-run scripted stress | Independent engineering enforcement evidence, never substituted for model-generated actions |
| New A1/A2/A3 | Supported only by this separately designed, frozen 720-run evaluation |

The old model study did not exercise the intended authorization boundaries because its legitimate task instructions constrained the model while conflicting instructions appeared in tool content. The model rejected or ignored those requests. A separate neutral-system pilot also produced no harmful calls. The new operational-objective design addresses the missing-attempt gap without optimizing jailbreaks, searching for a weaker model or changing the trusted principal's authority to match the model's objective.

## Paper artifacts and remaining limits

Use the [main risk figure](../results/agent-authorization-study-001/figures/unauthorized-commit-risk.pdf), [workflow figure](../results/agent-authorization-study-001/figures/workflow-export-publication.pdf), [condition table](../results/agent-authorization-study-001/analysis/condition-results.csv), [run index](../results/agent-authorization-study-001/analysis/run-index.csv), [methods/integration text](authorization-paper-integration.md) and [reproduction guide](authorization-reproduction.md). The original fourteen analysis/figure files reproduced byte-for-byte on this host before a presentation-only legend adjustment. All six original plot files and the original figure manifest remain preserved; the extended manifest additionally binds the publication layout derivative. No data or statistics changed. The original reproduction receipt is [recorded separately](verification/authorization-reproduction.json).

These results demonstrate architecture contribution in a fixed synthetic single-host, single-agent testbed under explicit attempted misuse. They do not estimate natural misuse prevalence, jailbreak susceptibility, human reviewer quality, multi-hop delegation security, control-plane compromise resistance or enterprise-scale performance. Synchronous JIT records and existing one-use controls do not establish independently delayed grant-expiration enforcement. Repeated fixed tasks provide limited attack diversity. C2 bundles several mechanisms; only the stated ablations isolate individual changes.

Before final IEEE submission, integrate these results beside the original negative/conditional findings in the existing manuscript, answer each original RQ with the appropriate evidence class, complete exact Appendix A locations, resolve outstanding primary-reference checks, verify author contributions and inspect the final IEEE PDF. The local files do not contain the live Overleaf source or referenced professor email; those checks remain author work.
