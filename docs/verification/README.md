# Reproduce live verification

From the repository root, with the deployed Compose services healthy, run:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_final
```

This command performs actual read-only source/image and network checks, real SPIRE issuance checks for the three specified lifetimes, and live control tests in fresh verification task namespaces. It does not rebuild, restart, reset, or contact a model provider. It retires only the task namespaces it creates, retaining their append-only service audit files and mock-tool snapshots.

`source-image.json` compares SHA-256 hashes of the host core source files against the files inside the running gateway image and records the actual image ID and health of every application container. All eight application services must use that same image. OPA and SPIRE use separately pinned image digests in Compose. The OPA policy file is mounted read-only from the verified host source.

`infrastructure.json` preserves actual JWT signature/audience validation, nominal claim lifetimes, direct-IP attacker isolation, absence of provider credential variables in container environments, and host/container clock brackets. HTTP clock brackets use the epoch time returned by gateway and administrator health endpoints. The bracketing interval includes transport and scheduling uncertainty; it is not an estimate of clock drift. The JWT claim-lifetime checks are issuance sanity checks and do not substitute for observed replay-expiry experiments.

`controls.json` records actual concurrent workflow, scope-forgery, duplicate-call, revocation, careful/rubber-stamp approval, and fresh-task isolation checks. `final-live.json` links the pass status of those checks to the source/image check and records namespace retirement. These are engineering checks, kept separate from the pilot and full research results.

Before refreshing evidence, the command retains the preceding snapshot under `history/<verification timestamp>/`. A source/image mismatch is preserved in `source-image.json` and `final-live.json`, and stops the live control tests until the deployment matches the intended source.

To compare the final pilot's preserved runtime source with the current checkout, run:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_pilot_source --pilot results/pilot-002 --output docs/verification/pilot-source-match.json
```

This compares SHA-256 hashes of exact bytes in the pilot manifest, its preserved source copy, and the current source. It covers experiment runtime, policies, topology, locked dependencies, and the identity/tool-evidence helpers. The host-only freeze utility and analysis/dashboard presentation are excluded from this specific comparison and are bound separately by the full-study freeze.
