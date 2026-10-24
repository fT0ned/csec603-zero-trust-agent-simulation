# Binding-response study: findings

Data: `results/binding-study-001` (150/150 planned runs completed, 0 failures, 0 reruns; manifest git commit 33f7f09d, freeze `configs/binding-study-freeze.json`). Pilot: `results/binding-study-pilot-001` (10/10). Offline analysis: `python -m analysis.binding_study --input results/binding-study-001 --output results/binding-study-001/analysis` (deterministic; full tables in `analysis/results.md`).

**Framing: mechanism verification (configuration-determined, scripted attacker). These are not hypothesis tests; the 30 repeats per condition are near-deterministic repeats. Counts and Wilson 95% intervals are descriptive.**

## What the data show (30 runs per condition)

| Condition | Stolen token executed any request | Data export (`crm.export` 5..9) executed | Attacker email executed | Attacker effect committed in independent tool ledger | Probe first refused (median, s after theft) | Containment (median, ms) | Legit agent allowed right after attack |
|---|---|---|---|---|---|---|---|
| C1 | 30/30 | 30/30 | 30/30 | 30/30 (150 records total) | 272.1 (token expiry) | n/a | 30/30 |
| C2 | 30/30 | 30/30 | 0/30 (recipient/scope policy) | 30/30 (150 records total) | 272.2 (token expiry) | n/a (logged only) | 30/30 |
| C2-AS | 0/30 | 0/30 | 0/30 | 0/30 | 0.06 | 2.30 (IQR 1.96-3.15; max 20.4) | **0/30** (reason `suspended`) |
| C3 | 0/30 | 0/30 | 0/30 | 0/30 | 0.06 | n/a | 30/30 |
| C3-AS | 0/30 | 0/30 | 0/30 | 0/30 | 0.06 | 2.56 (IQR 2.07-3.29; max 50.8) | **0/30** (reason `suspended`) |

Wilson 95% intervals: 30/30 is [0.89, 1.00]; 0/30 is [0.00, 0.11]. No exposure value was right-censored: in C1/C2 the probe was refused only when the JWT-SVID expired (about 272 s after theft; the last successful attacker request was about 267 s after theft, median); in the other conditions the first attacker request was refused. C1 and C2 attackers executed 55-56 requests each.

- **A stolen bearer token works until it expires in C1 and C2.** C2's policy blocked the exfiltration email to `archive@attacker.test` but allowed the in-scope `crm.export offset 5 limit 5`, so each C2 run leaked 5 records the legitimate owner never requested (within the 10-record workflow cap, since the owner used 5). C2's audit flags the impersonation (30/30: socket-peer origin differs from the run's expected origin) but takes no action.
- **C3 (sender-constrained token) makes the stolen token useless from the first request** (30/30 denied with `binding_proof_missing`), while the legitimate agent, which holds the key, kept working (30/30 completed the task and 30/30 allowed after the attack). No availability cost appears in this scenario.
- **C2-AS contains an impersonation at the first mismatched request** (denied with `origin_mismatch`; detection to deny-list active median 2.3 ms; all later attacker probes `suspended`). The audit row carries `response_action=suspend_and_revoke`, `trigger=origin_mismatch`, `detection_to_containment_ms`.
- **Availability cost (honest limitation of AS): the legitimate agent is locked out too.** In C2-AS and C3-AS the legitimate agent's next request was denied with reason `suspended` in 30/30 runs. Because suspension is triggered by a request carrying the stolen token from the wrong origin, any holder of a leaked token can deny service to the real agent. C3-AS shows this most clearly: C3 alone already defeats the thief with no lockout, whereas adding auto-suspend turns a failed theft attempt into an outage for the real agent.
- **Graduated response:** only the impersonation/origin-mismatch path suspends and revokes. The coercion path (exact parameter provenance) is implemented as a label only (`response_action=require_approval`, `trigger=parameter_provenance`) and was not exercised in this study (no coercion arm); approval logic was not changed. This is a response taxonomy, not a tested coercion defence.
- **Audit evidence held in all conditions:** hash chains valid 30/30 per condition, C2-family rows carried the full required fields, and the five-case tamper suite flagged 150/150 alterations per condition. The PA audit count matched the records captured from responses in every run (a run would have been marked evidence_failure otherwise), and attacker effects were read from independent tool ledgers, not from gateway claims.
- **Overhead of C3 (descriptive, concurrent runs on one host):** median of per-run median gateway round trips C3 54.88 ms vs C2 54.84 ms (difference 0.04 ms); PA authorization 1.96 vs 2.10 ms; client-side proof signing (key load plus ES256 signature, library import excluded) median 8.9 ms (IQR 7.7-9.4) per request in a fresh Python process. Runs of different conditions overlapped in time with different load, so a difference of a few ms is within noise; this is not a controlled benchmark.

## What it cannot show

- Statistical generalisation. The attacker is scripted and the repeats are near-identical by design; results follow from configuration. Counts such as 30/30 describe these runs.
- Protection against an attacker who compromises the agent-client container: the private key lives there, so binding would not help (and the attacker would share its network origin, so origin-based auto-suspend would not trigger either).
- Realistic origin attribution: the attacker is told apart only by its Docker container address on one host. Behind NAT/proxies or with a shared egress address, origin mismatch is not a reliable theft signal.
- Early theft or timing variation: theft is fixed at 30 s after receipt (shorter than the earlier study's 120 s); the exposure of C1/C2 is therefore about TTL minus 30 s minus issuance offset, a property of the TTL, not a measured distribution of attacker behaviour.
- Coercion/prompt-injection behaviour, real LLM agents, or multi-host deployments.
- DPoP is a faithful simplified variant: signature, thumbprint binding, `ath`, `htm`/`htu`, `iat` skew (+/-60 s) and per-run `jti` replay cache are checked; there is no server-supplied nonce, the `htu` is the gateway's view of the request URL, and the replay cache is in memory per run. The thumbprint is registered by the trusted harness rather than during issuance by SPIRE.

## Cost summary

C3 adds one asymmetric signature per request on the client and one verification at the PA; C2-AS/C3-AS add one extra HTTP call (gateway deny-list update) on the first mismatch only. No paid LLM calls were made.
