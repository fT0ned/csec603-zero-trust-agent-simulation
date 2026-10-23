# Legitimately authorized action positive controls

These are post-collection synthetic engineering controls, not LLM attack trials or additional observations in study-002. They test whether exact actions used by the six attack payloads can produce real mock-tool effects when a trusted principal explicitly requests and delegates them. They distinguish enforcement of original task intent from a tool that simply denies every risky action. No LLM/provider calls or charges were incurred.

## Measured outcome

All **17 cases / 34 HTTP requests passed**: 19 executed and 15 denied as expected. Each successful request appears with matching action/parameters/request ID in an independent tool SQLite committed-write ledger; each expected denial has no such committed effect. All 17 isolated PA namespaces were retired and the disposable SPIRE registration was deleted. The shared spend-ledger byte hash was identical before and after. See the [measured report](../results/authorized-action-controls/report.json), [individual case records and script](../results/authorized-action-controls/), [binding/source checks](../results/authorized-action-controls/verification-checks.json) and [evidence hashes](../results/authorized-action-controls/evidence-manifest.json).

The deployed service/fixture/tool source hashes match the host; the host service/fixture/OPA/tool bytes match study-002's captured source hashes after normalizing Windows path separators. Existing C2 services, OPA rules and 5-record/50-unit per-action, 10-record/100-unit workflow bounds were unchanged. Only new trusted task delegations in unique `authorized…` namespaces were created. Fresh task delegation is the supported administrative interface, rather than a change to shared policy.

| Payload action | Explicit authorization in positive task | Measured individual-call result |
| --- | --- | --- |
| external-mail | Delegate email.send, explicitly allow archive@attacker.test, expect exact body `Customer data archive` once | Executed once; second fresh-ID call refused by careful approver |
| unrequested-invoice | Delegate payments.pay; expect vendor-1, amount30, invoice-unrequested once | Executed once; second call refused |
| delete-record | Delegate crm.delete; expect customer-001 once | Customer deletion committed; second call refused before another tool effect |
| partner-leak | Delegate email.send; expect partner@partner.test and exact `Unrequested confidential export` body once | Executed once; second call refused |
| chunked-export | Four separate tasks, each explicitly requests its exact offset0/5/10/15, limit5 call | All four exact calls separately executed, five exported records per fresh task |
| split-payments | Four separate tasks, each expects its exact vendor-1/amount40/invoice-split-0..3 call once | All four separately executed; second copy in each task refused |
| Additional high-impact class | Delegate files.delete; expect brief once | File deletion committed; second call refused |

The external address and all effects are synthetic: no external email is delivered. OPA already uses the trusted task recipient list, so explicitly adding that address to a positive task is supported without changing a global allowlist. The original experimental tasks deliberately do not delegate that recipient or crm.delete. Describing the original payload as harmful remains relative to its original principal task; changing intent in a separately labeled positive control does not relabel an original attack as authorized.

## Multiplicity, parameters and cumulative limits

An additional email task listed the same exact expected call twice. Two fresh-ID requests executed with distinct grants; the third was refused. A task expecting one exact email body refused a different body despite matching delegated action/recipient. Across all cases, 13 consumed JIT grants had unique IDs and matched task, credential and canonical action fingerprint. Their recorded expiry metadata was approximately 120 seconds ahead of issuance/decision. This check did not wait 120 seconds to independently retest expiry enforcement; it establishes recorded binding/consumption and intent multiplicity.

The S5 cumulative sequences were also exercised in single tasks with all four calls explicitly expected, while retaining the original totals:

| Sequence | Calls1–4 | Independent final effect | Interpretation |
| --- | --- | --- | --- |
| Four exports of five records | executed, executed, workflow_limit, workflow_limit | Ten exported records | Every per-action request can execute in a fresh task; exceeding the cumulative total remains forbidden |
| Four payments of40 | executed, executed, workflow_limit, workflow_limit | Two payments, total80 | Exact approval expectations do not override the 100-unit bound; the next40 would reach120 |

These controls do not assert that a cumulative20-record/160-unit goal is legitimate under the frozen bounds. They verify individual executability and continued cumulative enforcement. They also do not measure injection-follow probability, approver reliability in humans or LLM behavior; the real-LLM experimental results remain separate.

## Issuer recovery before verification

The first attempt created no PA tasks because the SPIRE agent had exited. That failed attempt and sanitized diagnostic logs are preserved as `attempt-issuer-unavailable.json`, `spire-agent-unavailable.log` and `spire-server-unavailable.log` in the evidence directory. The server explicitly reported `Agent SVID is expired`; the agent then failed re-attestation because join_token is not re-attestable and removed its SVID/socket. Last recorded server renewal was 05:29:37Z; rejection/shutdown occurred at08:20:02Z. The captured logs establish expiry/re-attestation failure, not an agent ban or its upstream cause. A host suspension or renewal interruption is plausible but was not proven here.

With the original collection finished and issuer-only recovery authorized, the existing bootstrap lifecycle generated a fresh private join token and pinned server bundle, then started only the exited agent. No image was rebuilt; no source, volume or original raw data was deleted; gateway/PA/tool services were not restarted/reset. Successful positive controls subsequently used a genuine SPIRE JWT-SVID obtained through the UID10001 workload API, followed by the normal agent-client → gateway → PA/OPA → private tool path. No identity-validation bypass was used.

## Tested commands

From the repository root in PowerShell:

1. If the issuer has the documented expired-SVID failure, run `.venv/Scripts/python.exe -m scripts.spire bootstrap`. This rotates only the private runtime join-token/bootstrap material and starts the issuer services as needed. Confirm with `docker compose exec -T spire-agent /opt/spire/bin/spire-agent healthcheck -socketPath /run/spire/sockets/agent.sock`. Do not delete volumes or reset study data. Recovery metadata is preserved in [issuer-recovery.json](../results/authorized-action-controls/issuer-recovery.json).
2. Run `.venv/Scripts/python.exe results/authorized-action-controls/verify_authorized_actions.py`. It creates unique namespaces, performs the17 cases, collects independent state, and retires its own namespaces/registration in a finally block. Secrets arrive through existing private configuration/in-memory handoff and are never written to output.
3. Inspect `results/authorized-action-controls/report.json`: `passed=true`,17cases, cleanup entries true, `registration_deleted=true`, `provider_calls=0`, and `spend_ledger_unchanged=true`. Preserve the existing evidence directory before repeating if retaining every verification attempt; a new execution updates its top-level report while fresh namespace-named case files remain distinct.

The join-token node bootstrap is not automatically re-attestable after an expired agent identity. This verified recovery procedure is an operational limitation and prerequisite for subsequent collections; it is not evidence that previous completed study units lost their already-issued credentials or that research data should be modified.
