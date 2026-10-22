# Container topology and verified dependency sources

The actual deployment uses SPIRE 1.14.1, Open Policy Agent 1.10.1 and Python 3.12.12. The selected images were pulled successfully on October 22, 2026; their immutable manifest digests are pinned in Compose and the Dockerfile. Dependencies are intentionally pinned versions, rather than claims about the newest release.

Primary sources checked during implementation:

- [SPIRE 1.14.1 release](https://github.com/spiffe/spire/releases/tag/v1.14.1)
- [SPIRE registration CLI source](https://github.com/spiffe/spire/blob/v1.14.1/cmd/spire-server/cli/entry/create.go), including per-entry JWT lifetime in seconds
- [JWT fetch CLI source](https://github.com/spiffe/spire/blob/v1.14.1/cmd/spire-agent/cli/api/fetch_jwt.go)
- [SPIRE server configuration](https://github.com/spiffe/spire/blob/v1.14.1/doc/spire_server.md)
- [SPIRE Unix workload attestor](https://github.com/spiffe/spire/blob/v1.14.1/doc/plugin_agent_workloadattestor_unix.md)
- [OPA 1.10.1 release](https://github.com/open-policy-agent/opa/releases/tag/v1.10.1)

Only gateway and policy-administrator ports are published, bound to host loopback. Files, email, CRM, and payments run as separate HTTP services on an internal tools network reachable only from the policy administrator. The gateway is connected to the client and control networks. OPA is connected only to the internal control network. Agent and attacker containers share only the client network. The attacker cannot resolve or connect directly to tools, policy administrator, OPA, or SPIRE.

The trusted host harness uses Docker administrative access to create and delete a fresh SPIRE registration per run. Only the agent-client container mounts the Unix workload socket, and it runs as UID 10001; the Unix attestor measures the requesting process UID. The SPIRE agent uses the host PID namespace so Unix peer process lookup works across containers. The attacker runs as UID 10002 without the socket and cannot obtain new identities. Join-token node attestation is a deliberately modest bootstrap mechanism for a single-machine study; it is not hardware attestation. The CA bundle is explicitly pinned at bootstrap, with insecure bootstrap disabled.

The host orchestrator receives the SPIRE token in memory, gives the copied bearer token to the separate attacker client for S3, and registers public verification keys and the SHA-256 credential ID at the policy administrator. No assumption is made that JWT-SVIDs contain a unique `jti` claim. Identity issuance does not prevent a stolen bearer token from being replayed.

Mock services use SQLite transactions and fresh run namespaces. Retrying one request ID with identical parameters returns the original result; changed parameters under that ID are rejected. Gateway and policy administrator must additionally make workflow reservation and JIT consumption atomic before calling these services. No real email is sent and no real payment is made.

Ground truth, transcripts and checkpoint exports are written by the trusted host harness. No service receives a mount of the host results directory. The threat model trusts the host, Docker administrator, gateway, policy administrator and issuer; it does not claim protection from their compromise.
