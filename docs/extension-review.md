# Extension review of the original repository

Review baseline: clean `main` commit `cd7a8e2ef`, local live clone `Phase2/GithubRepoLive`, origin `fT0ned/csec603-zero-trust-agent-simulation`. The separate FrozenTimingV2 checkout is historical and was not modified. Review performed 2026-11-17 before extension model collection. This is a source/evidence review, not an editorial review of the separately written paper.

## Architecture and execution

`compose.yaml` runs SPIRE server/agent, OPA, gateway/PEP, policy administrator, files/email/CRM/payments mock applications, legitimate client and thief. Front, control, tools, identity and admin networks separate trust boundaries. Only gateway/PA/dashboard have loopback host ports; attacker has no workload socket or tools/control connectivity. Containers share one Docker/WSL2 VM on one Windows PC. This is network/process isolation, not independently hosted enterprise validation.

`scripts/spire.py` pins the trust bundle, uses join-token node attestation and Unix UID workload selectors, registers/fetches real signed JWT-SVIDs with `csec603-gateway` audience and configurable lifetime, and removes registrations after runs. These are real SPIRE credentials but not hardware attestation. Root/control/Docker compromise is outside the threat model.

`testbed/service.py` validates identity through PA, checks a gateway credential digest deny-list, takes origin from the socket peer, and serializes authorization/JIT dispatch/effect accounting per run. C2-family delegates action lists, recipient/vendor restrictions, per-call and aggregate limits to `infra/opa/policy.rego`. The careful approval routine checks exact requested action/parameter multiplicity; grants are one-use and expire. Tools implement actual synthetic state mutations in SQLite with request-ID deduplication. They send no external email and move no money.

`testbed/runner.py` implements S1–S5, creates fixtures/identities/control state, runs an LLM or scripted agent, records action timing and independent application state, runs stolen-token clients, and exports condition-visible audit and separately protected truth. `authorization_study.py` supplies explicit objectives and a separate authority/effect oracle. `binding_study.py` measures replay and legitimate availability. `final_study.py` plans all three, uses linked infrastructure/timing reruns, a host one-second clock monitor and keep-awake. Part A/B/C schedules and concurrency differ; timing cannot be read as a randomized model/platform comparison.

`testbed/agent.py` validates explicit provider/model IDs, retains sanitized requests/responses and usage, and reserves money transactionally in shared SQLite before calls. Unknown charges stay reserved. It supports DeepSeek Flash and an exact GPT-4.1 mini snapshot, with no fallback. `prompts.py` contains unchanged original and neutral profiles. Temperature 0 and planning seeds do not establish independent draws or immutable DeepSeek weights.

`audit.py` verifies an append-only hash chain against an independently held count/hash checkpoint and tests five tamper copies. Hash chains detect manipulation relative to a trusted checkpoint; they do not establish truthfulness of a compromised logger. `analysis/` separates descriptive summaries, authority studies, binary uncertainty, paired comparisons, Holm adjustments, censoring and freeze eligibility. The report layer deliberately qualifies configuration-determined results that older generic hypothesis labels handle poorly. Dashboard/easyboard are presentation surfaces and are not the measurement authority.

## Tests, configs, docs and archived evidence

Baseline suite: **189 passed**, 13.51 seconds, one upstream Starlette/AnyIO deprecation warning. Extension pre-pilot suite initially **201 passed** (12 additive security tests), 12.18 seconds. JUnit evidence is in ignored `.runtime/extension-*-tests.xml` until sanitized verification export. Existing tests cover live topology, tool effects, token/proof controls, audit isolation/tamper, measurements/probes, frozen manifests, export/dashboard behavior and failure handling. Passing them does not certify new OAuth interoperability or enterprise-scale resilience.

Config/reproducibility review covered final-study, authorization, binding, engineering/pilot and older freeze configurations, requirements pins, Dockerfile/Compose, orchestration/verification scripts, frozen-study protocol/findings, methodology/analysis plans, architecture/runbook, literature/reference and feedback matrices. Historical protocols describe historical runs and must not be silently updated to imply new evidence. The complete original `results/final-study-001` directory and final freeze's source list have a **45,977-file raw-byte preservation inventory** in `.runtime/extension-original-manifest.json`. New code is under `testbed/extension/`; no original frozen source is edited. Source-level review is broad; no claim is made that every byte of every historical transcript was manually reread.

## Confirmed gaps and defects

| Finding | Evidence and implication | Extension treatment |
|---|---|---|
| Unsigned delegation list, no multi-hop verifier | `fixtures.py` installs trusted `chain`; Rego tests authority attributes but never signatures or delegation transitions. Original evidence is trusted single-hop authority only. | New signed capability issuer/attenuation/ledger and actual A/B identity exchange; malformed-chain controls. |
| Original C3 is experimental PoP, not full RFC 9449 | `binding.py` takes harness-registered thumbprint; no token `cnf.jkt`, server nonce, normalized URI or DPoP authorization scheme. | Preserve original C3 name in history with explicit qualification; add `C3-9449-E` laboratory profile and a requirements/gap table. |
| No suspension recovery | `service.py` exposes suspend/revoke/retire but no re-attestation/rebinding recovery. | New admin recovery after fresh SVID fetch, capability exchange and bound key rotation. Old revoked capabilities remain revoked. |
| HTTP 429 not retried in original wrapper | `agent.py` reserves then records non-200 as provider failure. | New wrapper separately reserves each attempt, bounded 1/2/4-second backoff, retains uncertain attempts. Frozen wrapper unchanged. |
| Provenance alone can overlabel benign actions | Original `audit.attribution` treats any exact parameter link as coercion, even if the action is authorized. Mere copied text is not causal proof. | New classifier also requires independently recorded invalid authority and authenticated origin; legitimate copied-parameter negative controls. |
| Origin is a controlled topology signal | A different socket peer identifies the known thief in this setup; NAT, proxies, same-container compromise or stolen signing keys can defeat that mapping. | Keep controlled assumptions explicit and separate possession/authority/accountability; no universal coercion detector claim. |
| All-or-nothing suspension harms availability | Original C2-AS/C3-AS revoke/suspend when origin differs. No recovery in original. | Failure-specific PAA vs suspend-all, availability and reissue/rebinding measurements. |
| Approval is deterministic and idealized | Exact intent lookup is not human delay, fatigue or error. | Clearly simulated asynchronous grid only after tier 1; no human-performance claim. |
| Stale SPIRE trust after long offline period | Initial setup failed unknown CA/expired cached node state; refreshing bundle alone did not repair old state. | Additive Compose override uses fresh state directories inside `.runtime/extension-spire-*`; old volumes preserved. Setup then passed. |
| Dashboard second launch conflicts | Port 8765 already occupied by existing dashboard; duplicate launch exited. | Existing dashboard retained; measurement uses separate loopback API ports. |

The staged scanner detects exact known secrets from ignored env files and forbidden local paths, including gzip payloads; it is not a full entropy/history secret audit. It must run before every extension commit. Provider credentials were copied from the emoji-stego DPAPI store without displaying them, and `.env` is confirmed ignored. Original USD 1.689988128 ledger charges remain under the USD 25 ceiling; they are not reset.

## Claims the original code/evidence does not support

1. Natural-model coercion prevention when no harmful action was attempted. The original final study records **0/300 followed instructions**; it does not establish a positive natural-model coercion attribution result. Part B explicit malicious objectives and scripted attacks answer different questions.
2. "C2 blocked 0/120": the accurate statement is **0/120 unauthorized actions succeeded under C2**, whereas C0/C1 each had 120/120 successes in the stated adversarial Part B aggregates. Do not invert blocking and success.
3. Fully compliant RFC 9449, multi-hop delegation, human approval quality, recovery effectiveness, mTLS comparison or multi-host resilience. These were untested in the frozen study.
4. Identity proves action legitimacy; short lifetime prevents initial bearer replay; DPoP prevents a coerced legitimate key holder from requesting an unauthorized action. Those conclusions do not follow from the mechanisms.
5. 100% attribution as a universal enterprise classifier. It concerns detectable controlled-origin replay and known provenance, assumes honest control-plane logging, and excludes unobserved coercion cases.
6. Independent repeat samples simply because 30 temperature-0 runs were performed, general enterprise latency at 32 workers, or rare-failure absence from zero observed failures. Payload/workload diversity and shared-host scheduling constrain inference.
7. An immutable DeepSeek model version, provider-internal reproducibility, or actual billed cost merely from token-rate estimates. Returned aliases/fingerprints and ledger ceilings are retained; balance reconciliation is separate.
8. Novel identity, OPA, OAuth or hash-chain mechanisms. The defensible contribution is the unified controlled PAA evaluation and enterprise-specific response/availability implications.

## New implementation boundaries

The extension conditions are separately named `C0-E` (opaque static key), `C1-E` (signed identity-only bearer), `C2-E` (capability/authority/intent enforcement and PAA), `C3-9449-E` (same plus signed token binding and nonce/replay checks). The extension PDP is transparent Python policy, not an OPA configuration change or an exact replication of the original C2 treatment. It reuses private synthetic apps and the frozen independent authority oracle, with separate run namespaces. Multi-hop exchange uses a trusted issued-capability ledger; nested `act` is provenance, while signed top-level scope/budget drives current authority. These choices must remain visible in analysis.

Primary technical sources: [RFC 9449](https://doi.org/10.17487/RFC9449), [RFC 8693](https://doi.org/10.17487/RFC8693), and the official provider/Ollama pages listed in the protocol. No new empirical literature percentage is imported as an effectiveness baseline. Dense literature synthesis and overall paper structure remain editorial work outside the user's authorized artifact edits.

## Post-freeze engineering counterexample: numeric intent accounting

The frozen extension gate and the reused frozen authority oracle compare approved calls using Python numeric equality but key usage counts by raw JSON canonicalization. Therefore amount25 and25.0 compare equal for approval while using different consumption keys. A second semantically identical approved payment can pass under a sufficiently large cumulative limit. Deterministic offline counterexample: docs/extension-intent-edge-case.json. This is a negative result for a universal one-use-intent guarantee (A3), not a new sampled experiment. The initial sealed-action scan found no observed duplicate-payment group; final scan follows collection.

A separately tested engineering repair is provided in testbed/intent_normalization.py, with tests/test_intent_normalization.py covering both numeric orders, legitimate first use, requested multiplicity and denial of unrequested/Boolean values. It is not installed in the frozen experiment, and no repaired-study effectiveness is claimed. Original frozen sources, the extension freeze and collected units remain unchanged. Both gate and oracle sharing this edge case is an oracle-validity limitation; report registered results alongside this counterexample.


Post-freeze URI check: `normalize_htu(https://example.test/a/%2e)` returns `/a` rather than `/a/` after decoding the unreserved dot and removing the trailing dot segment. Evidence: `docs/extension-uri-edge-case.json`. This is another implementation-level limit on full RFC9449/RFC3986 normalization conformance. The fixed `/tool` collection endpoint does not exercise it. Frozen code remains unchanged; no repair effectiveness is claimed. Reference: [RFC3986 sections2.3,5.2.4 and6.2.2, DOI10.17487/RFC3986](https://doi.org/10.17487/RFC3986).
