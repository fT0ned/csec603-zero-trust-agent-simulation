# Integrating the authorization experiment into Report 2

This supplement belongs in the existing IEEE manuscript as a separate evaluation of the approved Zero Trust research questions. It preserves the original real-model null findings, scripted enforcement evidence and conditional timing sensitivity. Measured confirmatory results must come from the completed, independently validated `agent-authorization-study-001`; the running collection is not a result.

## Methodology text for the manuscript

We evaluated whether enterprise authorization controls independently constrain actions selected by an authenticated large language model (LLM) agent. The experimental harness supplied an explicit operational objective, while the principal's legitimate authorization was registered separately through a trusted control-plane interface. For example, the model was instructed to export twenty customer records in four batches of five, whereas the principal authorized a maximum of ten records. The agent could select its own tool calls and parameters, receive actual gateway responses, retry, stop or pursue additional operations. The harness did not inject a prewritten action sequence into the tool loop. The experiment therefore measures the contribution of authorization enforcement under attempted misuse, rather than the probability of inducing misuse through prompt injection.

The security configuration was the independent variable. C0 used a static bearer credential with broad authority; C1 used a SPIRE-issued workload identity with the same broad authority. C2 additionally applied task-scoped policy, trusted principal restrictions, cumulative workflow accounting, simulated approval and action-bound, single-use just-in-time grants. C2-noWF removed cumulative limits, and C2-RS replaced careful approval with rubber-stamp approval. All conditions validated credentials at the same gateway. Identical objectives, principal state, tool schema, synthetic inputs and model settings were used within each applicable comparison. Condition-dependent allow/deny feedback could change subsequent agent behavior; that difference was an observed consequence of the treatment.

The design comprised four adversarial objectives and two authorized positive controls. The adversarial objectives exercised out-of-scope deletion, a vendor outside principal authority, an in-scope but unrequested payment, and cumulative export authority. Positive controls required an authorized ten-record export or one authorized payment. Each applicable task/condition cell had thirty independent task namespaces, yielding 720 planned runs. Seed labels matched task replicas and randomized execution order; they did not seed provider-side sampling. The model was the supported DeepSeek alias, with temperature zero, thinking disabled, 1,024 response tokens and eight maximum model rounds. The provider alias is mutable, and requested/returned identifiers, fingerprints, settings and complete interaction records were retained.

Two exploratory pilots preceded confirmation. The first exposed premature termination on recoverable tool errors and mutable nested audit snapshots. Its failures and observations were preserved. After engineering repairs, the second pilot completed all 24 planned cells, generated unauthorized requests in all fourteen adversarial cells and completed both legitimate tasks in all five conditions. Independent adjudication verified the effects and audit records. Neither pilot was pooled with confirmation. A published precollection Git tag sealed the final protocol, source, configuration, sample allocation and analyzer before confirmatory requests. Collection used the existing cumulative USD 4 provider ledger without resetting historical expenditure.

The experimental unit was a complete task run, not a tool call. For scope, principal and approval scenarios, the primary outcome was at least one independently committed unauthorized positive effect. For the workflow scenario, it was an actual exported-record total above the principal's ten-record limit. Attempts, denials, policy allowances, zero-effect writes and committed effects were distinguished. Request identifiers, action parameters and private-tool write records were reconciled against final tool state. A successful model response or HTTP status did not establish a committed effect. Read-only accesses, which lacked an independent write ledger, were reported separately.

The prespecified family contained ten paired comparisons: C0 and C1 against C2 in four adversarial scenarios, C2 against C2-noWF for exports, and C2 against C2-RS for approval. Binary comparisons used exact two-sided McNemar tests with Holm correction across the complete family. We reported risk differences, paired run-bootstrap intervals and per-condition Wilson intervals. A support judgment required a directional absolute risk difference of at least 0.20, adjusted p below 0.05, a complete planned matrix and valid source, runtime, raw, audit, effect and clock evidence. These criteria apply only to the new experiment. The existing original hypotheses retain their prior judgments.

## Interpretation boundaries

The intended enterprise implication is that authentic identity and legitimate authority are separate properties. Broad authentication-only access permits actions outside the accountable principal's request unless another control restricts them. Workflow limits can provide containment after authorized partial progress: the first ten records may be exported while later batches are denied. Selective approval is preventive only to the extent that the approval decision matches trusted intent. The simulated careful approver and rubber-stamp ablation establish the consequences of those decision rules, not measured human review accuracy.

Accountability must be described as agreement between condition-visible audit fields and independently recorded principal, issued agent, task, delegation, action and effect. The direct objective is known to the harness. It is not evidence of prompt injection, coercion detection or a model's internal intention. Baseline missing audit fields must remain missing in condition-visible scoring; host truth cannot be used to reconstruct better baseline logs.

The new collection does not repeat credential lifetime or revocation measurements. The existing reviewed timing sensitivity conditionally supports H1/H1b, while the original study remains quality-vetoed. The absence of harmful S2/S5 calls in the old real-model experiment remains an informative limitation of that experimental entry point. Scripted stress independently demonstrates enforcement against forced requests. Neither the new study nor scripted stress retrospectively confirms original H2/H2b/H2c.

## Threats to validity

| Threat | Consequence and reporting requirement |
| --- | --- |
| Explicit objectives exceed authorization | Estimates control contribution under attempted misuse; does not estimate natural misuse or jailbreak prevalence |
| Single mutable model alias | Preserved transcripts support exact reanalysis, not identical future generation or fixed model weights |
| Small fixed synthetic task catalog | Findings apply to tested boundaries and parameters; no claim of exhaustive reachable authority or production attack coverage |
| Single trusted principal-to-agent record | Enforces stored principal scope; does not validate multi-hop attenuation or external directory ownership |
| Trusted issuer, administrator and evidence host | Control-plane compromise, recovery and colluding services remain outside scope |
| Idealized simulated approval | No measurement of human decision quality, fatigue, queueing or response time |
| Synchronous JIT grant issuance and consumption | One-use binding is exercised; delayed independent grant-expiration races are not measured by this study |
| Local transport and four concurrent workers | Report action/authorization costs as this testbed's measurements, not enterprise service-level guarantees |
| Thirty repeats per cell | Even zero failures has Wilson upper 95% bound about 11.4%; deterministic-looking observations do not prove zero risk |
| Agent chooses subsequent behavior | Counts of attempts can differ after denials; primary run comparisons avoid conditioning solely on attempted calls |
| Zero-effect and partial calls | Retain durable write records while separating positive effects; workflow conclusions require actual totals above the bound |

## Professor feedback and manuscript placement

| Feedback | Material to integrate | Required final manuscript action |
| --- | --- | --- |
| Explicit answers to all three RQs | Retained timing evidence; new authorization evidence; trusted audit agreement | Write RQ-specific conclusions with evidence class and limits |
| Identity does not establish intent | Separate operational objective and trusted principal state | Explain in methodology, architecture and conclusion |
| Cumulative workflow authority | Export objective, independent totals and noWF comparison | Include the workflow figure and distinguish prevention from containment |
| Selective high-impact approval | Requested versus unrequested invoice and RS comparison | State simulated reviewer assumptions and human-quality limitation |
| Risk/control mapping and recommendations | Table below and existing architecture/evidence matrix | Number, caption and discuss each artifact in the body |
| Complete Appendix A | Existing feedback IDs plus this extension | Fill exact final section, table, figure and page locations after pagination |
| Formal conclusion | Preserve separate evidence classes and negative findings | Place Conclusion immediately before References |
| IEEE language and reference audit | Existing source-quality register and writing guidelines | Define acronyms at first main-body use; verify citations and inaccessible claims |

## Enterprise recommendation matrix

| Priority | Recommendation | Prerequisite | Expected contribution | Implementation risk or limit |
| --- | --- | --- | --- | --- |
| 1 | Store principal intent and delegation outside model-controlled inputs | Protected administrator interface and trustworthy principal source | Independent tool/action and parameter authorization | Incorrect or compromised trusted state can authorize the wrong action |
| 1 | Mediate every tool request through a policy enforcement point | Network isolation and no direct tool bypass | Prevent out-of-scope action effects | A policy or gateway outage must fail closed and remain distinguishable from credential expiry |
| 1 | Enforce cumulative budgets atomically | Reliable per-task state, idempotency and conservative uncertain-effect accounting | Bound workflow effects even when individual requests are small | State races or premature reservation release can exceed authority |
| 2 | Apply intent-aware approval to eligible high-impact actions | Trusted requested-action parameters and remaining multiplicity | Prevent unrequested effects within otherwise valid tool scope | Rubber-stamp or inaccurate review removes this protection |
| 2 | Bind audit records to principal, issued agent, task, decision and independent effect | Protected checkpoints and independent tool evidence | Support accountable investigation and detect inconsistent evidence | Hash chaining alone does not protect mutable context or a compromised evidence host |
| 2 | Use short-lived identities with separately tested revocation | Reliable issuance, rotation and per-request rejection | Bound stolen-bearer exposure under the conditional timing evidence | Workload attestation alone does not prevent replay of an issued bearer copy |

The live Overleaf source and referenced instructor email are not supplied locally. Exact manuscript locations, final IEEE rendering, bibliography resolution, author contributions and submission remain separate author steps; repository preparation cannot truthfully mark them completed.
