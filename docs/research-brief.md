# Engineering review of the Phase 2 research brief

Reviewed October 22, 2026. This is an implementation handoff, not a replacement source of truth or a change to the research design. No experimental findings are claimed here.

## Document authority and inventory

The source of truth is `../../enterprisePhase2_FINAL.docx`, titled "Leopard Report 2 - Source of Truth", dated October 21, 2026. Read the original whenever resolving details. Official requirements, instructor feedback/email, and writing guidelines override the project brief.

All six Phase 2 source documents were reviewed:

| Document relative to Phase2 | Purpose |
| --- | --- |
| `enterprisePhase2_FINAL.docx` | Research design, hypotheses, metrics, implementation plan, freeze checklist, paper plan; includes the control-path figure |
| `0Documentation/Report 2 Requirements rev 1.0.pdf` | Official Track B requirements, structure, artifacts, reproducibility rules, and rubric |
| `0Documentation/Leopard_Report1_Feedback.pdf` | Group-specific corrections and required enterprise recommendations |
| `0Documentation/writing guidliens.pdf` | Mandatory language, acronym, evidence, and presentation guidance |
| `0Documentation/Leopard___Zero_Trust_AI_Agents___CSEC_603_600___Enterprise_Security___Research_Paper.pdf` | Submitted Report 1, original RQs, evidence matrix, gaps, and reference list |
| `0Documentation/Appendix A.docx` | Blank feedback-response matrix template |

The instructor email and live Overleaf source are referenced in the brief but are not present in this directory. Their contents have not been independently checked. Existing references were read as part of the supplied paper; external bibliographic verification has not yet been performed.

## Research commitment

Retain the approved topic, Track B, original three research questions, and specified design. The central claim under test is that identity authenticity alone does not establish action legitimacy. Separate a genuine but coerced agent from an attacker replaying its stolen credential.

- RQ1: credential theft/replay exposure and revocation behavior.
- RQ2: authorization, scoped delegation, cumulative authority, approval/JIT, and security versus operational cost.
- RQ3: reliable attribution to agents and accountable principals, checked against independent ground truth.

Use the exact original RQ wording in the manuscript and verify against Overleaf before submission. The supplied Report 1 PDF was checked for the wording and scope.

## Fixed experimental design

| Condition | Design |
| --- | --- |
| C0 | Non-expiring static API key; broad tools; typical minimal logs |
| C1 | SPIRE-attested short-lived JWT-SVID; broad tools; identity-aware logs |
| C2 | C1 identity plus per-request OPA authorization, trusted task-scoped delegation, workflow counters, approval, one-use expiring JIT grants, and full audit |
| C2-noWF | C2 with workflow limits removed; S2 and S5 only |
| C2-RS | C2 with an always-approving simulated approver; S2 and S5 only |

All conditions validate credentials and consult the same gateway deny-list on every request. C1 versus C0 primarily tests finite credential lifetime in this design; it does not isolate attestation or use stronger revocation.

| Scenario | Purpose |
| --- | --- |
| S1 | Legitimate tasks, false denials, completion, overhead, approval burden; includes harmless external input for attribution controls |
| S2 | Prompt injection through tool content coerces the genuine agent |
| S3 | A separate attacker client replays a copied credential on a fixed schedule |
| S4 | Compare immediate deny-list revocation with waiting for credential expiry |
| S5 | Individually permitted actions combine to violate a whole-task limit |

Main credential lifetime: 15 minutes. S3/S4 sweep: 5, 15, 60 minutes. These are planned settings from the brief, not measured values. Begin planning at 30 trials per cell; the pilot fixes the final count, with increases for S2/S5 only as specified in the brief. The main matrix is 450 trials and the two cut-down variants add 120, before additional lifetime/revocation cells. Freeze a complete run manifest to avoid double-counting the main 15-minute cells in the sweep.

Use one real LLM model for headline results and a scripted always-obeying mode as a separate worst-case check. Keep model/settings, task and payload lists, seeds/order, tools/data, timing, and hardware comparable. Optional mTLS and a second model are separate extensions.

## Components to implement

1. Docker Compose topology with pinned dependencies, health checks, private tool networks, and repeatable clean resets.
2. Mock file, email, CRM, and payment services with low/high-impact actions and a resettable data snapshot.
3. SPIRE identity issuance and workload attestation, plus the C0 static-key mode.
4. Python PEP gateway that is the only tool access path; credential validation and deny-list checks in every condition.
5. OPA policy engine plus a distinct policy administrator for revocation, JIT grants/removal, and session suspension.
6. Trusted delegation store and atomic per-task workflow accounting; the agent cannot supply its own authority.
7. Careful and rubber-stamp simulated approvers, with one-use expiring action-bound JIT grants.
8. Real LLM tool-calling loop and separate scripted mode; complete prompt/response/tool-call capture.
9. Fixed task/attack fixtures, replay/probe clients, revocation trigger, pairing, run metadata, timing, and outcome recording.
10. Append-only hash-chained audit, separately protected hash/count checkpoints, independent ground-truth recorder, and tamper verifier.
11. Analysis scripts producing metric tables, uncertainty intervals, attribution confusion matrices, and paper-ready plots from preserved raw data.

## Measurements and interpretation

Record unauthorized outcomes per attack run, harmful-action success, reachable authority, cumulative authority, nominal remaining lifetime, observed replay exposure, revocation propagation and first-denial delay, attribution accuracy, audit completeness/tamper detection, latency/authorization overhead, legitimate-task outcomes, approval burden, and injection follow rate.

The actual contribution centers on chained actions, attribution, observed revocation, and security versus cost. Configuration-guaranteed denials, nominal expiry differences, and hash-chain checks are sanity checks. A JWT-SVID is a bearer credential: attestation must not be credited with preventing replay of a stolen copy.

Keep observed exposure distinct from nominal remaining lifetime. Probing resolution limits timing precision; still-valid credentials are right-censored at the observation window. Never average censored values as if they were completed observations. Distinguish policy refusal from model/tool errors, timeouts, and incomplete tasks.

Use Wilson intervals for rates, appropriate paired/unpaired tests as specified in the brief, risk differences and bootstrap time differences, Kaplan-Meier/log-rank treatment of censored times, and Holm correction. Freeze the comparison families and analysis rules before full runs. Report null and negative results.

## Parameters still to settle before full runs

- Main provider/model snapshot, supported lowest-temperature setting, prompts, API access, and spending limit.
- Verified software versions and published payload sources; fixed payload/task catalog.
- Exact action scopes, data/recipient/payment limits, careful-approver rule, and JIT duration.
- Attribution algorithm and the independent ground-truth schema.
- Theft/revocation timing, fixed probe intervals, observation windows, and final per-cell run count.
- Minimum practical differences for each applicable hypothesis, defined before full experiments.
- Pilot token/currency cost, runtime/concurrency budget, full run manifest, and Git freeze tag.

Do not silently fill these with fabricated versions, citations, or measured values. The brief says the design is decided, but explicitly leaves these operational values open.

## Engineering questions to resolve during the pilot

These are implementation checks derived from the fixed design, not changes to it:

- Workflow limits must remain correct across concurrent requests. Reserve/check/update counters atomically and define failure, retry, and duplicate-call semantics.
- Delegation records, input provenance, and request origin must come from trusted components. Agent-supplied headers or arguments must not forge them.
- The attribution scorer sees only the evidence available to the relevant condition. It must never see harness labels. External-input exposure alone cannot establish coercion; score parameter-level causal links and normal activity too.
- Include S5 payloads for which the careful approver does not independently mask the workflow-limit effect. Analyze approval-dependent payloads separately to isolate C2 versus C2-RS.
- Separate harmless replay-validity probes from policy-denied harmful actions. Otherwise C2 authorization can make a still-valid credential appear expired.
- Validate how issued credentials are uniquely identified for revocation and logs; do not assume an unverified JWT claim exists.
- Make one-use JIT permission consumption atomic and bind it to the approved action parameters, task, and identity.
- Prevent tool bypasses through published ports or shared networks. The separate attacker must reach the gateway but not internal tools/control state.
- Protect checkpoints and ground-truth files from writes/reads by the system under test as specified, including final-record deletion tests.
- Parallel long-lifetime runs can contend for resources. Record and control concurrency so it does not confound latency comparisons.
- Define infrastructure-failure reruns and retain their records; never exclude a run because of its security outcome.

## Paper work supported by the implementation

Continue in the existing Overleaf project. Preserve and refocus the literature review to justify the experiment. Produce all ten required analytical artifacts, including results, comparative analysis, risk/control mapping, recommendations, and threats to validity. Appendix A maps instructor feedback to exact changes; Appendix B supplies reproducibility materials. Answer all three RQs explicitly and place Conclusion immediately before References. Apply the required academic-language and reference audit.

The testbed is a single-machine, single-agent study with an idealized approver and a fixed model/date. Control-plane compromise, multi-agent delegation, enterprise scale, recovery, and the optional untested variants remain limitations. Do not present the testbed as proof for production enterprises.

## Next implementation sequence

Resolve and document open design values; build the services and controls; validate isolation/reset/timing; run a small pilot; check cost and every metric; complete the pre-run checklist and tag the frozen design; collect full runs and tamper tests; analyze preserved raw data; then integrate measured results into the paper.
