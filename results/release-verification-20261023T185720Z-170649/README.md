# Postcollection application release verification

This is engineering verification with **zero provider calls**, separate from all research collections. Actual release build/recreate and live infrastructure/control verification completed at 18:58 UTC on 2026-10-23; the subsequent endpoint checks and controlled host-runner fault completed after the quota pause.

1. `before.json`, `build.log` and `recreate.log` preserve the measured release boundary. Only gateway, PA, agent-client, attacker and the four tool services were recreated. SPIRE server, SPIRE agent and OPA retained their original container/image IDs; all eleven services retained their volume mounts.
2. `verify-final.log` and the current `docs/verification/{source-image,infrastructure,controls,final-live}.json` record real SPIRE issuance, OPA/control enforcement, network isolation, clocks, source/image matching and own-namespace retirement. `source-image-after.json` reconfirms current core host bytes equal the deployed application image and all eight application services share one healthy image.
3. `verify_endpoint_semantics.py` is the reproducible host-only utility; `endpoint-semantics.json` retains all 15 measured assertions and actual responses. C0/C1/C2 streams execute the baseline, then actual revocation terminates their stream as credential_denied. A trusted PA RPC reuses an authentic earlier validation verdict after revocation to exercise the stale-validation race; this is explicitly a controlled RPC race test, not a forged workload request. C2 policy scope denial and suspension are measurement failures, and denied deletion leaves the brief readable. All four own namespaces were retired and SPIRE registrations removed.
4. `../qa-runner-probe-failure-20261023T225507Z-d2119cf8/verification.json` records the real namespace-scoped missing-file fault. The actual streaming client and host runner both retain tool_failure, allowed=true/tool_error, null event/first-denial, valid raw seals and valid audit/checkpoint; the PA is actually idle after retirement. It is an expected **failed engineering unit**, not a successful research replicate. Its terminal batch marker was added outside sealed raw data after execution to unblock dashboard CLI discovery; the helper now emits that marker on future executions. The verification records the executed helper's original hash.
5. `pytest.log` records 105 tests passing in 11.13 seconds, with one upstream Starlette/AnyIO deprecation warning. No test failures remain.
6. `after.json` and `verification-summary.json` record all 13 release assertions passing, unchanged shared spend ledger and all 48 predefined research metadata/raw-manifest hash guards unchanged. This release guard does not claim to rehash every original research payload; independent research integrity validation remains preserved separately.

Dashboard restart and browser verification belong to the lead's separate release checks. No global reset, volume deletion, research mutation, provider call, SPIRE/OPA restart or extra application rebuild was performed for the endpoint/fault tests.

Reproduce the endpoint checks from the repository root while PA is idle:

```powershell
.venv/Scripts/python.exe -c "import runpy;runpy.run_path('results/release-verification-20261023T185720Z-170649/verify_endpoint_semantics.py',run_name='__main__')"
```

The utility reuses its local report filenames; preserve this measured directory before any repeat. The guarded fault helper always creates a fresh uniquely named directory:

```powershell
.venv/Scripts/python.exe -m scripts.verify_runner_probe_failure --execute
.venv/Scripts/python.exe -m pytest -q
```
