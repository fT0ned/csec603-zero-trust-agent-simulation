# Reproducing the separate authorization evaluation

Run commands from `Phase2/GithubRepoLive`. Keep all original result directories and the existing ignored `.runtime/spend.sqlite` ledger. This experiment uses the deployed SPIRE/OPA/gateway/private-tool infrastructure; it does not require another credential-lifetime sweep.

## Read and reproduce without provider calls

Start with [the protocol](agent-authorization-protocol.md), [source audit](agent-authorization-source-audit.md), [pilot review](agent-authorization-pilot-review.md) and [paper integration text](authorization-paper-integration.md). The original source of truth and professor feedback remain in the parent Phase2 directory. The original testbed release is `phase2-delivery-v1`; the new precollection seal is `agent-authorization-freeze-v1`.

The first exploratory pilot, `results/agent-authorization-pilot-001`, has retained failures and an independent audit-quality veto. The repaired second pilot, `results/agent-authorization-pilot-002`, has a passing final review. Neither is part of the 720-run confirmatory manifest in `results/agent-authorization-study-001`.

Reproduce a completed collection's analysis into a **fresh** output directory:

```powershell
.venv/Scripts/python.exe -m analysis.authorization_study --input results/agent-authorization-study-001 --output .runtime/reproduced-authorization-analysis
.venv/Scripts/python.exe -m scripts.plot_authorization_study --report .runtime/reproduced-authorization-analysis/report.json --output .runtime/reproduced-authorization-figures
```

These commands make no provider requests and do not change raw observations. The analyzer verifies the captured source hashes and every run seal, independently reconstructs model dispatch and real feedback, checks trusted authorization, reconciles private-tool writes/state, verifies gateway and retained control-audit records, and reconstructs continuous clock quality. A full-study support judgment additionally requires the executing analyzer to match the captured freeze. Use the captured analyzer or the exact freeze checkout if later working-source changes occur. Never use the original `analysis.cli` to assign the new study's hypotheses.

`analysis/report.json` contains source bindings, full condition tables, all ten primary comparisons, uncertainty, evidence errors and eligibility. CSV files provide condition results, paired contrasts and run-level data. The `figures/` directory contains PDF/SVG/PNG paper figures and their checksum manifest. The general unauthorized-effect endpoint and the workflow-specific actual limit-breach endpoint are distinct columns; compare the endpoint named in each contrast.

The principal authorization and model objective are in each run's `fixture.json` and `trusted-setup.json`. `transcript.json` preserves actual provider requests/responses and generated tool calls. `attempts.jsonl`, `recorded-actions.json` and `actions.jsonl` distinguish generated dispatch from gateway responses. `tool-before.json` and `tool-ground-truth.json` independently establish clean state and committed effects. Audit/checkpoint/control records permit independent integrity checks. A raw manifest is a checksum record, not a digital signature; the protected host and committed archive remain trust assumptions.

## Run a new exploratory replication

Use the configured host and its existing ledger. Check Docker health and provider access without printing credentials. A new computer must receive the retained spending ledger securely from its owner before paid continuation under this aggregate budget; a fresh empty ledger must not bypass historical spending. Secrets and the active ledger intentionally are not in Git.

```powershell
.venv/Scripts/python.exe -m pytest tests -q
.venv/Scripts/python.exe -m scripts.verify_authorization_runtime --output .runtime/new-runtime-check.json
.venv/Scripts/python.exe -m testbed.authorization_study --config configs/agent-authorization-pilot.json --output results/agent-authorization-pilot-NEW
```

Choose a genuinely new output name. Existing directories are refused, including partial attempts. The pilot configuration is real LLM mode, not the scripted engineering agent. The trusted fixture source installs authority through the administrator API, while the provider receives only the operational objective and ordinary tool schema. It cannot supply its own principal permissions. Inspect actual generated attempts, authorized controls, independent effects and evidence validity before planning confirmation.

## Reproduce the frozen collection procedure

The historical precollection command was:

```powershell
.venv/Scripts/python.exe -m scripts.collect_authorization_study --config configs/agent-authorization-study.json --output results/agent-authorization-study-001
```

That output directory is preserved and must never be reused. A live replication must use a fresh directory, the same immutable freeze or a separately reviewed new protocol, and the retained aggregate ledger. The existing freeze gate binds all 720 cells and refuses changed controls, objectives, settings, analyzer or sample counts. It verifies the pushed Git tag and actual deployed source/policy/clock checks before model calls. It does not permit an edited configuration to masquerade as the same confirmatory protocol.

The seal records exact captured host bytes and exact Git blob bytes separately. This preserves the original Windows CRLF representation without changing frozen files. When reproducing on another checkout or operating system, Git may supply LF bytes. For exact collection reproduction, restore **only the seal's listed sources** from that collection's committed `source/` snapshot into an isolated checkout, copying bytes unchanged; retain the immutable tag and original private configuration/ledger. Do not normalize historical raw data or relax the hash gate. For offline analysis, captured source and byte-preserved observations already provide the needed evidence.

The wrapper keeps the host awake and samples host wall time against monotonic time every second. After collection, inspect `batch-status.json`, `clock-quality.json`, `runtime-verification.json` and the independent analysis report before treating completion as accepted evidence. An interruption, budget/provider error, model step limit or failed evidence gate remains visible. There are no automatic replacement runs and no outcome-driven sample additions. A mutable model alias prevents guaranteed regeneration of identical behavior; deterministic reanalysis of preserved evidence is the stronger reproducibility claim.

## Dashboard inspection

Open `http://127.0.0.1:8765` after launching the existing dashboard. CLI collections appear read-only in history. Read the real-LLM mode, pilot/full phase, operational-objective prompt profile and separate protocol label before interpreting comparisons. New scenario names are intentionally distinct from legacy S1–S5. The legacy experiment form does not author or freeze this new protocol; use the commands above.

CSV/JSON exports and traces describe the selected collection. Keep pilot and confirmatory outputs separate. A passing export checksum is not scientific acceptance; inspect the analysis and quality report too. The dashboard's generic harmful-attempt/commit columns project independently adjudicated unauthorized effects for this new protocol and do not mean prompt-injection following. PDF figures are exportable only when bound by their local figure manifest.

## Remaining paper work

Integrate the new methods, measured tables/figures and limitations into the existing Overleaf manuscript, while retaining original null and conditional findings. Fill Appendix A with actual final manuscript locations, resolve outstanding primary-reference checks, verify author contribution statements, and inspect the final IEEE PDF. Neither the live Overleaf source nor the referenced instructor email is available in the supplied files, so those checks cannot be claimed completed by this repository handoff.

## Reanalysis from the exported ZIP

The ZIP places captured `source/` beside `results/`. In a fresh extracted directory, copy `source/` byte-for-byte to `results/source/`, then execute the included `analysis.authorization_study` module with working directory `source/`, input `../results` and a fresh output `../reanalyzed`. This supplies the frozen analyzer and its expected captured-source layout. The actual exported archive reproduced all seven analysis outputs byte-for-byte; see `docs/verification/authorization-included-source-reanalysis.json`. The additional publication workflow figure only changes legend placement; frozen plot files and their original manifest remain preserved.
