# Paper evidence integration guide

This file supplies implementation-to-paper mappings and draft analytical artifacts. It is not a submitted manuscript and contains no invented experimental findings. Continue in the existing Overleaf project, preserve the approved original research questions, and place Conclusion immediately before References. Verify the original question wording against that project before submission. All generated counts must be labeled “measured in this testbed” and retain condition, agent mode, phase, model/date, denominator, units and uncertainty.

## Artifact inventory

| Required artifact | Source or implementation material | Integration requirement |
| --- | --- | --- |
| Feedback response matrix | [Detailed source-page mapping](feedback-response-matrix.md), plus Appendix A summary below | Repository actions mapped to professor feedback; exact manuscript locations and final status remain pending |
| Literature evidence matrix | [Standalone 16-entry matrix and authoritative foundations](literature-evidence-matrix.md), [32-reference verification register](reference-verification.md) | Includes method, findings, limits, original quality rating, evidence type and design justification; inaccessible primary claims remain explicitly unverified |
| Comparative analysis table | Condition table below plus generated metrics/comparisons CSV | Insert measured cells only after collection and manifest verification |
| Architecture/workflow diagram | [Deployed SVG](figures/deployed-architecture.svg), [editable Mermaid](figures/deployed-architecture.mmd), [implementation explanation](architecture.md) | Shows separate issuance/delegation, OPA PE→PA administration, gateway PEP mediation and actual PA tool dispatch, distinct attacks, and independent evidence boundaries |
| Risk/control mapping | Table II below | Distinguish prevention, containment, detection and response |
| Research-gap table | Table III below | Explain addressed scope and residual limitations |
| Recommendation matrix | Table IV below | Separate measured support from architectural rationale |
| Simulation design and RQ/hypothesis tables | [Numbered Tables VI–IX with frozen implementation links](experimental-design.md), frozen manifest and analysis plan | Report exact versions, model settings, timing, run count, thresholds, reset procedure and interrupted-collection boundary |
| Results tables/plots | `analysis/results.md`, CSV, JSON and standalone SVG | Confirm no mixed modes or pilot/full results; interpret null results |
| Threats-to-validity table | Table V below | Include dataset bias, model version, attribution assumptions and single-machine constraints |

The ten artifact categories have repository source material. This does not mean ten finalized manuscript artifacts: comparison/recommendation/results cells await verified full-study evidence, bibliography verification remains partial where primary access failed, and all final manuscript locations/captions/body discussion require integration. The literature and feedback documents above were prepared during collection without modifying the frozen protocol or claiming full-study outcomes.

## Table I Comparative condition design authors’ work

| Criterion | C0 | C1 | C2 | C2-noWF | C2-RS |
| --- | --- | --- | --- | --- | --- |
| Credential | Non-expiring static key | SPIRE JWT-SVID | SPIRE JWT-SVID | SPIRE JWT-SVID | SPIRE JWT-SVID |
| Shared validation/deny-list | Every request | Every request | Every request | Every request | Every request |
| Task/action authorization | Broad tools | Broad tools | OPA per request | OPA per request | OPA per request |
| Delegation source | No enforcement | No enforcement | Trusted task record | Trusted task record | Trusted task record |
| Cumulative workflow bound | Absent | Absent | Present | Removed | Present |
| High-impact approval | Absent | Absent | Careful simulated | Careful simulated | Always approving simulated |
| One-use expiring JIT | Absent | Absent | Present | Present | Present |
| Audit evidence | Typical minimal | Identity-aware | Full principal/action/provenance | Full | Full |
| Scenarios | S1–S5 | S1–S5 | S1–S5 | S2/S5 | S2/S5 |
| Measured outcome/overhead | Not measured here | Not measured here | Not measured here | Not measured here | Not measured here |

Table I defines the comparison before results. C1–C0 primarily concerns finite bearer-credential lifetime; it does not isolate attestation from expiry or provide a different revocation mechanism. C2 is a combined package except for the two specified ablations.

## Table II Risk and control mapping authors’ work

| Trust or risk assumption | Control | Primary effect | Measurement or evidence limit |
| --- | --- | --- | --- |
| A copied static key remains useful | Short-lived attested issuance | Bounds exposure after theft | S3 real-time replay; attestation does not bind a stolen bearer token |
| Expiry acts as immediate revocation | Shared gateway deny-list and PA | Response and exposure containment | S4 command/active/first-denial timestamps; single gateway |
| Authenticated requests are legitimate | Per-action task-scoped OPA decisions | Prevention and authority containment | S2/S3 outcomes and reachable authority; combined C2 package |
| Request-by-request limits bound whole-task harm | Atomic workflow counters | Cumulative blast-radius containment | S5 C2 versus noWF; control for approval-dependent payloads |
| Every in-scope high-impact action reflects intent | Careful approval with one-use JIT | Conditional prevention, smaller privilege window | C2 versus RS; idealized approver, no human study |
| Agent-provided authority/provenance is trustworthy | Control-plane delegation and trusted origin capture | Prevents forged authority/evidence | Boundary tests; full control-plane compromise excluded |
| Logging an identity proves cause | Origin and parameter-level provenance | Detection/attribution | S1 false alarms plus S2/S3 confusion matrix versus independent truth |
| Audit integrity follows from a hash chain alone | Separately protected hash/count checkpoints | Post-hoc tamper detection | Alter/delete/reorder/final-truncation tests; prevention is not claimed |
| Control-plane components can be implicitly trusted operationally | Network isolation, separate roles and protected stores | Reduces attack surface | Configuration and bypass tests; adversarial control-plane compromise excluded |

Table II ties controls to different risk effects. Runtime monitoring alone detects; active authorization and revocation enforce a response. No row constitutes a claim of production-enterprise effectiveness.

## Table III Research gaps and tested scope authors’ work

| Report 1 gap | Contribution attempted here | Residual gap |
| --- | --- | --- |
| G1 Delegation in policy | Trusted principal/task/delegation fields enter per-request decisions | Single chosen schema; no interoperable standard established |
| G2 Cumulative authority | Matched S5 with workflow-limit ablation | Fixed totals and payloads; other workflow semantics untested |
| G3 Coercion versus impersonation | Same pipeline, independent truth, normal-input controls | Attribution depends on observable parameter links and origin; not causal proof of internal cognition |
| G4 Interoperability | Documented component interfaces | Cross-vendor authorization interoperability remains untested |
| G5 Common evaluation | Same testbed/task/metric set across conditions | Author-selected dataset is not a community benchmark |
| G6 Lifetime versus revocation | Real-time lifetime sweep and shared deny-list comparison | Single-machine propagation; stale registrations and recovery not comprehensively evaluated |

Table III identifies the part of each gap the implemented study can address. Whether the contribution is empirically supported depends on the preserved results and their uncertainty.

## Table IV Enterprise recommendations authors’ work

| Priority | Recommendation | Evidence to cite | Expected outcome | Prerequisite and implementation risk |
| --- | --- | --- | --- | --- |
| 1 | Enforce task and action scope at every tool gateway | Architectural rationale; add S2/S3 measured contrasts when available | Reduces excessive reachable authority | Trusted delegation, complete mediation; policy mistakes can deny legitimate work |
| 1 | Operate revocation separately from lifetime | Bearer-token semantics; add S4 measured timings | Faster response to detected theft | Reliable deny-list distribution; distributed propagation remains unmeasured here |
| 1 | Protect PE, PA, PEP, issuer, delegation and telemetry | Professor feedback and stated trust boundaries | Reduces control-plane attack surface | Separation of duties and hardened infrastructure; control-plane compromise outside this study |
| 2 | Bound cumulative workflow authority atomically | Add S5 C2/noWF effect with intervals | Contains chained-action blast radius | Correct cross-tool totals and retry semantics; contention and failed reservations |
| 2 | Use short-lived workload identities where issuance is reliable | SPIFFE/SPIRE guidance; add S3 observed/censored exposure | Limits residual credential life | Attestation and rotation availability; stolen bearer credentials still replay |
| 2 | Require meaningful approval for selected high-impact actions | Add approval-dependent C2/RS results | Prevents intent violations when review is reliable | Idealized reviewer here; approval fatigue and real human behavior unmeasured |
| 2 | Bind telemetry to principal, agent, delegation, origin and action | Add S1/S2/S3 attribution confusion and false alarms | Supports distinct coercion/impersonation responses | Trusted provenance and protected logs; observational links can be ambiguous |
| 3 | Anchor audit hash/count checkpoints separately | Add tamper-copy test outputs | Detects changed/reordered/truncated history | Store isolation and checkpoint durability; chain checks do not prevent compromise |

Table IV prioritizes recommendations by architectural necessity and implementation dependency. Replace “add” entries with the exact run IDs/table locations after evidence exists. Recommendations based on guidance must remain labeled as guidance.

## Table V Threats to validity authors’ work

| Category | Threat | Mitigation and remaining limit |
| --- | --- | --- |
| Internal | Stateful counters, reused credentials or retry side effects contaminate runs | Clean resets, new registration/token, idempotency/concurrency tests; preserve reset evidence |
| Internal | Concurrent lifetime trials perturb latency | Fixed and recorded concurrency; isolate latency collection where practical |
| Internal | Model ignores payloads, hiding weak controls | Report injection-follow rate separately; scripted worst-case checks in their own partition |
| Internal | Approval masks workflow-limit effects | Prelabel approval-dependent payloads; include S5 chains that do not require approval |
| Construct | Authorization denial mistaken for expiry | Harmless credential-validity probes; preserve validation versus policy reasons |
| Construct | External-input exposure mistaken for coercion | Parameter-level provenance links; normal harmless-input controls; independent truth |
| Construct | Ground truth leaks into prediction | Separate stores and scorer interfaces; audit the prediction input schema |
| Construct | Individual calls treated as independent runs | Run-level analysis and paired resampling; action ratios labeled descriptive |
| Statistical | Rare failures absent in small samples | Wilson intervals and precision caveat; freeze count, no outcome-driven extension |
| Statistical | Censored values treated as observed lifetimes | KM/log-rank and boundary-validity rate; no ordinary averages of censored times |
| External | One agent/model alias/date and synthetic enterprise dataset | Preserve requested/returned model identifiers, documented version and fingerprints; the mutable provider alias prevents guaranteed immutable-model reproduction |
| External | Ideal careful approver and one-machine network | State best-case approval assumption and limited timing generalization |
| External | No control-plane compromise, multi-agent delegation or recovery | Explicit scope exclusions; future work rather than implied validation |
| Reproducibility | Provider drift, missing raw files or unpinned versions | Preserve model alias/version/date/fingerprint with the drift limitation, freeze manifest, dependency versions, hashes and complete raw archive |

Table V bounds interpretation of every result. A measured effect in this testbed is evidence about this testbed and workload, not proof about all enterprise deployments.

## Appendix A feedback response draft

| Report 1 feedback | Repository response | Manuscript location/status |
| --- | --- | --- |
| Add formal conclusion answering each RQ | Evidence integration instructions preserve RQ-specific judgment and limitations | Pending manuscript integration; exact location must be supplied |
| Separate short lifetime from revocation | Separate S3/S4 protocols and survival/time metrics | Pending measured results and manuscript integration |
| Separate authenticity from action legitimacy | Distinct S2 coercion and S3 replay; attribution scoring versus independent truth | Pending measured results and manuscript integration |
| Add dedicated enterprise recommendations and matrix | Table IV draft with prerequisites and implementation risk | Pending author review and manuscript section 13 |
| Complete architecture, comparison and risk mapping | Deployed SVG/editable Mermaid, Tables I/II and `docs/architecture.md` | Deployed topology and controls verified in `docs/verification`; manuscript figure integration remains pending |
| Evaluate cumulative workflow authority | S5/noWF comparison defined in analysis plan | Pending full empirical collection |
| Approval prevents only with reliable review | Approval-dependent C2/RS strata; idealized-approver limitation | Pending empirical collection |
| Protect the critical control plane | Explicit boundaries and Table II/IV guidance | Repository isolation/configuration verified in `docs/verification`; manuscript integration remains pending and control-plane compromise is outside scope |
| Add abbreviations and academic-language fixes | Carry forward official writing checklist | Pending manuscript-wide edit; no completion claimed |
| Audit IEEE references and preprints | Preserve evidence classifications and verify metadata | Pending bibliography audit |
| Do not pool incompatible studies/percentages | Analysis partitions mode/phase/model/scenario/lifetime/revocation | Implemented in derivation code; manuscript review still required |
| Cover page first, honest contribution table | Submission requirement recorded here | Pending human authors and final PDF |

Appendix A must describe changes actually made in the paper. Repository readiness does not mean manuscript corrections are complete. The professor's email and live Overleaf contents require separate access if unavailable locally.

## Appendix B reproducibility checklist

Record the private repository commit/freeze tag, hardware and operating system, container digests, dependency versions, requested/returned model alias, documented version, system fingerprints and sampling settings, provider terms/access date, task/payload sources and adaptation notes, trusted scopes, workflow budgets, approver rules, JIT duration, timings/windows/concurrency, pairing and rerun policy, final manifest, raw artifact hashes, costs and budget ceiling. State that the provider's mutable alias prevents guaranteed immutable-model reproduction. Supply numbered launch/reset/run/analyze/export instructions and verify them on a clean environment. Include raw/processed summaries and the calculation method; do not expose live provider keys or replayable testbed credentials.
