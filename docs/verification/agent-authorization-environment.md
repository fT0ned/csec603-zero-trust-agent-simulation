# Authorization-study environment audit

Audit date: 2026-10-24 Asia/Dubai (live evidence stores UTC). Baseline release:
`phase2-delivery-v1`, commit `a996a78bedd3a0f53ce13da1a52ecb1505de56ed`.
These are engineering observations, never real-LLM experimental observations.

## Reused infrastructure and readiness

The initial checkout was clean. All eleven Compose services were healthy. The
only active Python processes were two dashboard instances; no collection was
running. No reset, volume deletion, secret rewrite, or provider inference request
was needed. SPIRE and mock-tool volumes and the shared spending ledger remain.

- `agent-authorization-infra.json`: actual JWT-SVID issuance at 300, 900 and 3600
  seconds; verified signature, audience and lifetime; network isolation; credential
  separation; host/container clock uncertainty brackets within one second.
- `agent-authorization-controls.json`: all seven live checks passed, including
  concurrent workflow accounting, ignored model-supplied authority, idempotency,
  careful/rubber-stamp approval divergence, fresh namespace state and revocation.
- Initial baseline: 105 tests passed before new-study changes, including actual
  pinned OPA policy execution, audit tamper detection, tool-state isolation,
  uncertain downstream effects and repaired credential endpoints. The latest
  full-suite run is retained in `agent-authorization-unit-tests.xml`; a subsequent
  concurrent development run observed 116 passes and one new-study test failure
  (mutable test-input aliasing in parameter-mismatch reconciliation). Final study
  validation must rerun the suite after the new harness and tests settle.
- `agent-authorization-trusted-boundaries.json`: six checks passed after the policy
  repair below. A payment to a separately authorized `vendor-2` committed; a payment
  to the old hardcoded vendor was denied. A principal-defined payment ceiling of
  20 and per-export ceiling of two were enforced. Forged request-body delegation
  and condition fields could not expand authority. Independent private-tool state
  contained exactly one payment of 20 and two exported records. Audit chain passed.

## Actual fault repaired before the feasibility pilot

OPA formerly hardcoded `vendor-1`, five records per call and 50 per payment even
though trusted delegation already carried `vendors`, `max_per_records` and
`max_per_payment`. This was adequate for the historical fixtures, whose trusted
values matched those constants, but was incorrect for another principal's bounds.
The current policy reads those three trusted fields and denies the affected action
when its required field is absent or its numerical ceiling is invalid. Existing
frozen sources, historical results, tags and findings were not rewritten. Eight
Rego tests now include alternate-vendor, lower-ceiling, missing-field and forged
outer-field regression assertions. OPA alone was restarted to load its bind-mounted
policy; no application rebuild or data-volume change was necessary.

## Trusted boundary and interpretive limits

The trusted host posts run configuration, principal identity, delegation, expected
intent and condition through the administrator endpoint. The gateway overwrites
origin and credential validation from socket/authentication evidence; the PA builds
policy input from its stored run. Tools and the agent cannot route to each other
directly, and the agent has no administrator or provider secrets.

This implementation enforces the stored final principal authorization. It records
the supplied delegation chain but does not independently validate attenuation
across multiple delegation hops or principal ownership in an external directory.
Describe new experiments as principal-bound scope enforcement, not a cryptographic
multi-hop delegation protocol. Careful approval is a deterministic simulated intent
comparison; rubber-stamp approval bypasses that comparison. JIT grants are generated
and consumed synchronously inside the PA, bound to task/action/credential, one use,
with a 120-second expiry; there is no independently delayed human approval or
public token-redemption service. Offline regression checks verify consumption,
intent multiplicity, duplicate behavior and TTL metadata. These tests alone do not
measure a delayed grant-expiration race.

The historical attribution heuristic detects external-data provenance/origin
patterns. For direct operational objectives in the new study, use trusted
principal/agent/task fields and independent tool ledgers as accountability ground
truth; do not call the objective prompt injection or reuse the old coercion label.

## Budget and isolation

The ledger read at the start of this audit contained 4,633 settled entries,
accounted cost USD 0.558286572, no unsettled reservations, and approximately
USD 3.441713428 remaining under the preserved USD 4 aggregate cap. This is a
point-in-time ledger observation, not a provider-balance reconciliation or a
guarantee of future available spend. A DeepSeek key was present; its value was
never printed. New paid calls must continue using the existing `Budget` class
and ledger. No paid calls were performed by this audit.

Fresh run IDs reset each tool namespace without changing historical namespaces.
The legacy `verify_controls` helper leaves disposable verification namespaces in
PA memory; their state is separate from experiment IDs. The new boundary verifier
retires its own run and deletes its SPIRE registration while preserving tool/audit
records. No experiment requires global service resets.

## Reproduction

From the repository with the existing environment loaded:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.verify_infra --output docs/verification/another-infra-check.json
.\.venv\Scripts\python.exe -m scripts.verify_authorization_boundaries
```

`verify_authorization_boundaries` writes its named verification artifact; use a
separate checkout/output amendment if preserving that artifact immutably. The
new study uses separate frozen evidence directories. Existing timing-repair checks
remain in `test_probe.py`, `test_endpoint_adjudication.py`,
`test_runner_probe_fault_scope.py` and `test_timing_sensitivity_gates.py`: failed
tools/transport are not treated as credential expiry, and clock corrections are
not reinterpreted as successful timing measurements.
