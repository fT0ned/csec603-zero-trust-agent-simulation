# final-study pilot review (results/final-study-pilot-001)

Pilot of the final-study protocol: 2 repeats per cell, S3/S4 at TTL 300 s only, real `deepseek-flash` (temperature 0, thinking disabled). 134 planned runs (A 68, B 56, C 10); 134 completed, 0 infrastructure failures, 0 reruns, 0 provider errors, 0 malformed model-action runs. Clock monitor: no wall-clock step (clock_passed true). Maximum absolute 120 s handoff error 0.015 s (monotonic scheduling). Raw seals verified for all three parts; `scripts.validate_collection` passes on Part A. Pilot data are descriptive and never pooled with the full collection.

## Checks asked for

- **Zero infrastructure failures / metrics populated:** yes, after one discovered bug (below). All Part A, B, C summaries carry the metrics the analyzers need; the combined analyzer ran end to end (`results/final-study-pilot-001/analysis`).
- **C3 / AS endpoints:** the stolen bearer token is refused at the first attacker request in C2-AS, C3, C3-AS (reasons: `suspended` after the origin-mismatch trigger in AS conditions, `binding_proof_missing` in C3). The first probe is therefore recorded as the observed denial (exposure 0 s, event observed) and not as an infrastructure failure. The legitimate LLM agent's DPoP-signed calls were accepted in C3 (availability check allowed 2/2 in S3/S4 and Part C) and refused after suspension in C2-AS/C3-AS (0/2): the availability cost of auto-suspend.
- **S4 now in C3/AS:** the operator revocation was still issued and its propagation recorded; `revocation_moot` is set because the credential had already been refused.
- **Cost:** USD 0.0367 for 134 runs (A 0.0181, B 0.0154, C 0.0033). Linear projection to 3,090 runs: about USD 0.85; with a 50% reserve about USD 1.27, on top of the existing ledger (0.83) that is about USD 2.1, below the USD 4 cap. No budget change is needed.
- **Model metadata:** returned model id `deepseek-flash` in all 386 requests, one system fingerprint.
- **Injection behaviour:** unchanged from earlier real-LLM work: in S2/S5 the model did not follow the injected instruction in this pilot (0/2 per cell), so C0/C1 versus C2 contrasts on S2/S5 are expected to be null in the full study; Part B (explicit objectives) supplies the cases where the model attempts unauthorized actions.

## Bug found and fixed before the freeze

The first pilot attempt (discarded, never committed) produced a Part C infrastructure failure: the model wrote an em dash in an e-mail body; the Windows default code page (cp1252) encoded it as byte 0x97, the container decoded it as a lone surrogate and the gateway answered HTTP 500. `container_request` and the attacker stream now use UTF-8 explicitly (regression test in `tests/test_final_study.py`). Earlier collections that used the same helper could in principle have hit this for non-ASCII model text; that is a limitation to state, not something changed retroactively.

## Not exercised by the pilot

TTL 900/3600 s windows, the 30-repeat statistics, timing reruns (none needed), the resume path, and long-run host stability. The full run's first stage (Parts B and C) and second stage (Part A) are monitored by the same code.
