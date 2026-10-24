# Binding-response study protocol (written before data)

Status: protocol fixed before any pilot or full data. Separately labelled follow-up to the completed authorization studies; it does not alter or re-analyse any earlier collection under `results/`.

## Why

The completed studies showed that a stolen JWT-SVID (C1/C2) can be replayed from another container until it expires, and that only C2's audit notices the impersonation (socket-peer origin differs from the run's expected origin) but merely logs it. Two treatments are added behind new condition names; C0, C1, C2, C2-noWF and C2-RS behave exactly as before.

## Conditions

| Condition | Definition |
|---|---|
| C1 | Short-lived SPIRE JWT-SVID, bearer only, no policy (as before) |
| C2 | C1 plus PA/OPA policy, audit and workflow limits (as before). Logs but does not act on origin mismatch |
| C2-AS | C2 plus automatic response: origin mismatch denies the request, sets the session `suspended`, clears grants, adds the credential to the gateway deny-list, and writes an audit row with `response_action=suspend_and_revoke`, `trigger=origin_mismatch`, `detection_to_containment_ms` |
| C3 | C2 plus sender-constrained credential (DPoP-style proof of possession, RFC 9449 spirit; RFC 7638 JWK thumbprint). The agent-client container creates an EC P-256 key at run start (file mode 0600, `/tmp/dpop/` in that container only). The trusted harness registers the JWK SHA-256 thumbprint as `binding_jkt` in PA run state. Each request carries a `DPoP` JWS (htm, htu, iat, jti, ath = SHA-256 of the token). `/control/validate` verifies signature, thumbprint equality, ath, htm/htu, iat within +/-60 s and per-run jti non-reuse; failures are `binding_proof_missing` / `binding_proof_invalid` |
| C3-AS | C3 plus the C2-AS automatic response. Origin mismatch triggers even when the binding check already failed |

Coercion signals (exact parameter provenance) never suspend in the `-AS` conditions; they only add `response_action=require_approval`, `trigger=parameter_provenance` as a label. Approval logic is unchanged.

## Per-run procedure (scripted, no model, no paid calls)

1. Fresh SPIRE registration and JWT-SVID, TTL 300 s; fresh task namespace; tools reset; independent tool snapshot before.
2. Legitimate agent-client (with DPoP proofs in C3/C3-AS) performs the fixed task through the gateway: `files.read brief`, `crm.export offset 0 limit 5`.
3. Theft occurs 30 s after credential receipt (shorter than the 120 s of the earlier study to save time; this is a separate study). The attacker container receives only the bearer token and run ID, never the private key.
4. Attacker burst: `crm.export offset 5 limit 5` (within C2 scope and limits, so a valid credential would be allowed) then `email.send` to `archive@attacker.test` (blocked by C2-family recipient/scope policy regardless of credential state).
5. Legitimate availability check: one `files.read brief` immediately after the burst.
6. Attacker probes `files.read brief` every 5 s until the first non-executed response or until TTL + 30 s after credential receipt (window end). A run with no denial by window end is right-censored.
7. Independent tool snapshot after; audit chain, checkpoint and five-case tamper suite; PA run retired; SPIRE registration and agent key deleted.

## Metrics per run

replay_attempts_allowed; first_attacker_success; burst export/email allowed; exposure_seconds (last executed attacker request, 0 if none); event_observed with first_denial_seconds and reason or censoring time; detection_to_containment_ms (AS conditions); legit_task_completed; legit_after_attack_allowed and reason (availability); committed attacker writes/records from the independent tool ledger; audit completeness and whether audit flags impersonation; tamper detection counts; legitimate-request end-to-end latency, DPoP signing time and authorization time.

## Design

Pilot: 2 runs per condition (10 runs), `results/binding-study-pilot-001`. Full: 30 runs per condition (150 runs), `results/binding-study-001`, concurrency 8, seed 4603 (shuffled order recorded in `manifest.json`). One rerun per cell is allowed, only for infrastructure failure, linked by `rerun_of`, never chosen by outcome. Sources are hashed in `configs/binding-study-freeze.json` before the full run.

## Analysis and framing

Offline, deterministic, stdlib only (`analysis/binding_study.py`). Counts such as 30/30 with Wilson 95% intervals, exposure medians/IQR with right-censoring reported as "> window" (never averaged), Kaplan-Meier-ready survival CSV, containment-latency distribution, availability-cost table, C3 versus C2 latency (run medians, descriptive). Every security contrast is labelled **mechanism verification (configuration-determined, scripted attacker)**. No hypothesis tests or p-values: the repeats are near-deterministic repeats of a mechanism, not samples from a population.

## Known limits (fixed in advance)

Single host; attacker distinguished by container IP; scripted attacker; the private key is stored in the agent container (an attacker who compromises that container defeats binding); origin attribution trusts the Docker network peer address; auto-suspend locks out the legitimate agent too and lets any token holder trigger a denial of service.
