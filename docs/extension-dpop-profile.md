# DPoP conformance boundaries

Original `C3`/`C3-AS`, in the unchanged frozen study, are **experimental proof-of-possession schemes inspired by DPoP**. Their harness-side key registration, Bearer scheme, absent signed `cnf.jkt`, absent server nonce and literal URI comparison are not full RFC 9449. Historical evidence remains immutable; no retroactive conformance claim is made.

`C3-9449-E` is a new **experimental laboratory profile with RFC 9449 resource-proof checks**, implemented in `testbed/extension/security.py`, `client.py` and `service.py`. Its name identifies the specification being evaluated, not certification of a full OAuth deployment.

| Requirement / behavior | New profile implementation | Scope or limitation |
|---|---|---|
| Asymmetric signature, `typ=dpop+jwt`, permitted `alg`, public JWK only | ES256/P-256, verify embedded public key and reject private `d` | Other permitted asymmetric algorithms are not implemented |
| `htm`, normalized `htu`, `iat`, `jti` | Method/URI verification, default-port and dot/unreserved normalization, no query/fragment in proof target, 60-second age bound | HTTP routing profile, no reverse-proxy canonicalization deployment |
| Access-token key binding | Issuer-signed capability `cnf.jkt`; compare proof JWK thumbprint | Capability is experimental JWT access token, not a SPIRE JWT-SVID with edited claims |
| Token hash `ath` | SHA-256 access token hash in resource proof | No refresh-token flow |
| Server nonce | Verifier-owned 120-second nonce context, checked in exchange/resource proof; resource rejection includes `DPoP-Nonce` | Proactive laboratory `/nonce` endpoint is additional; authorization-server nonce error flow is not full OAuth error interoperability |
| Replay | Per-verifier `(jkt,jti)` cache, pruned only after acceptance window | In-memory service state; restart persistence/distributed cache out of scope |
| DPoP authorization scheme | Resource requires `Authorization: DPoP …`; bearer token-only request refused | Token-only attacker uses the correct scheme to isolate lack of key possession |
| Duplicate headers | Exactly one Authorization and one DPoP proof required for bound requests | HTTP parser/proxy interoperability is not separately certified |
| Resource error | HTTP 401 plus DPoP WWW-Authenticate and nonce | JSON audit response is laboratory-specific |
| Authorization-server proof at exchange | Validated SVID actor plus DPoP proof; issuer embeds bound thumbprint | Custom exchange JSON is RFC 8693-inspired, not complete OAuth grant/metadata protocol |
| HTTPS transport | Not implemented inside the private Docker networks | RFC 9449 requires HTTPS in deployment; this alone prevents claiming complete deployment conformance |
| mTLS binding | Not implemented | No comparison to mTLS is claimed |

Replay/valid-owner tests validate this exact profile. DPoP proves key possession; a coerced legitimate key holder still signs a valid proof, so delegated authority must be checked independently. Source: [RFC 9449](https://doi.org/10.17487/RFC9449), with [RFC 7638](https://doi.org/10.17487/RFC7638) thumbprint primitive inherited from original binding code.
