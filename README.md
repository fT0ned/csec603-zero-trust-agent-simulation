# Easiest way to see the results

Double-click **`Start-Dashboard.bat`** in this folder for the existing testbed studies listed in that dashboard (nothing to install, read-only). The separate PAA extensions use the protocols and completion reports linked below. Details and troubleshooting: [docs/easy-dashboard.md](docs/easy-dashboard.md). From a terminal: `.venv\Scripts\python.exe -m easyboard` (or `python -m easyboard`).

# Zero Trust for Agentic AI

Group Leopard's CSEC 603 Track B testbed compares static keys, real SPIRE workload identity and a combined OPA/delegation/workflow/approval/audit treatment. It includes separate agent and stolen-credential clients, private mock enterprise tools, real LLM tool calling, a local dashboard and reproducible analysis.

The parent enterprisePhase2_FINAL.docx governs the design; official requirements and professor feedback take precedence. Start with the [plain-English experiment guide](docs/quick-start.md) or [handoff](docs/handoff.md). Detailed references: [research brief](docs/research-brief.md), [method and limitations](docs/method.md), and [numbered runbook](docs/runbook.md). Current status is in [durable progress notes](docs/progress.md).

1. Start Docker Desktop, then run `powershell -ExecutionPolicy Bypass -File scripts/setup.ps1`.
2. Configure the ignored `.env` from `.env.example` for paid runs and preserve the spending ledger.
3. Run `powershell -ExecutionPolicy Bypass -File scripts/launch.ps1` and open [localhost:8765](http://127.0.0.1:8765).
4. Load an engineering or separate enforcement preset. Original full collection requires its preserved study-freeze-v2 checkout; new source changes intentionally fail that original freeze gate.
5. Inspect trials and export CSV/JSON, tables, plots and a sanitized reproducibility bundle.

Scripted engineering evidence and real-LLM findings are always labeled separately. The original1200-unit collection completed, but its preserved validation failed after a proven clock correction; see [quality adjudication](docs/study002-quality-review.md). Original S2/S5 transcripts show no harmful agent attempts, so those real-model results do not establish gateway prevention. Only synthetic enterprise data enter the tools and prompts; mock actions send no email and transfer no money.

The default provider is DeepSeek Flash. Dated model metadata, returned identifiers, system fingerprints, usage and complete interaction transcripts are retained. Its API alias is mutable, limiting exact model-version reproducibility. Provider secrets never enter containers or repository evidence. A shared SQLite reservation ledger enforces the aggregate spending cap across workers and batches.

See [analysis rules](docs/analysis-plan.md), [paper artifact mappings](docs/paper-artifacts.md) and [verification evidence](docs/verification). This single-machine study does not establish production-enterprise effectiveness.


The separate [enforcement extension](docs/enforcement-extension-protocol.md) uses one neutral system prompt across C0/C1/C2 and unchanged actual controls. Its36-unit real-LLM exploratory pilot completed and again recorded no harmful attempts; [exact transcript findings](docs/neutral-pilot-findings.md) preserve this negative result. The separately tagged390-unit scripted stress collection completed and passed its validation: C0 and C1 each committed120/120 harmful requests, while C2 committed0/120. [Measured enforcement findings](docs/enforcement-stress-findings.md) explain the payload-specific scope, workflow and approval effects, uncertainty and limitations. The [completed conditional timing sensitivity](docs/timing-sensitivity-findings.md) preserves the original veto and all failed attempts. [Positive controls](docs/authorized-action-controls.md) verify that exact payload actions execute when explicitly authorized.


## Main study (used in the paper)

`results/final-study-001` (protocol `docs/final-study-protocol.md`, findings `docs/final-study-findings.md`). Reproduce: `python -m scripts.collect_final_study run --config configs/final-study.json --output results/NEW`, then `python -m analysis.final_study --input results/NEW --output results/NEW/analysis` and `python -m analysis.final_study_report --input results/NEW --analysis results/NEW/analysis`. View with `Start-Dashboard.bat`.

## PAA extension study

Additive work is on branch `extension-study`; original frozen sources and `results/final-study-001` are preserved. The [protocol](docs/extension-study-protocol.md), [review](docs/extension-review.md), [PAA specification](docs/extension-paa-specification.md), [DPoP boundaries](docs/extension-dpop-profile.md), [pilot review](docs/extension-pilot-review.md) and [progress](docs/extension-progress.md) distinguish natural-model results from scripted controls. Original user requirements and the later 3B-model addition are archived [verbatim](docs/extension-user-requirements.txt).

Pilot: four models (DeepSeek Flash, exact GPT-4.1 mini snapshot, pinned Qwen2.5 7B and 3B instruction/tool models), original/neutral prompts, three payload families, five seeds each: **0/120 exact follows**. Only 41 runs actually read the payload-bearing brief; this is a limited-exposure null, not evidence of universal model resistance. No stratum passed the registered 2-of-5 selection rule. The full collection completed **1,570 primary runs (1,574 preserved raw units)** across scripted coercion/joint/negative controls, signed multi-hop delegation, PAA vs suspend-all/recovery, and model-driven objective/replay arms. All **216 tests pass**; **45,977 protected original files** are byte-identical. [Completion report](docs/extension-completion-report.md) and [publication tables/figures](results/extension-study-001/publication) contain the exact results. Conservative extension ledger cost: **USD 0.208131045**, including uncertain reservations. The paper is not edited by this work.

One-command reanalysis of the archived extension (Windows PowerShell):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/reproduce_extension_report.ps1
```

Fresh collection, using ignored `.env` configured from `.env.extension.example`, Docker Desktop/NVIDIA GPU and the preserved spending ledger:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/reproduce_extension_report.ps1 -Mode Collect
```

The collection command checks the remote freeze tag, exact model digests, source/runtime hashes, clocks and network boundaries. It never overwrites the archived study and refuses silent model substitution. Token budget is USD 25 including preserved prior ledger charges. This single-PC deployment is network-separated, not a multi-host enterprise or full OAuth/RFC 9449 conformance demonstration. DOI publication steps are in [the archive guide](docs/extension-zenodo-steps.md).

The pilot also recorded nine unauthorized task-drift writes across six Qwen3B runs and five false coercion labels; these are separate from exact payload follows. Post-freeze deterministic checks exposed a numeric one-use-intent accounting bug (25 versus25.0) and an encoded trailing-dot URI-normalization edge. Both are disclosed in the report. A unit-tested numeric repair is supplied separately and was not installed in frozen conditions. [Release](https://github.com/fT0ned/csec603-zero-trust-agent-simulation/releases/tag/extension-study-001); DOI login steps remain with the owner. PDF export uses the official pure-Python FontTools4.67.0 wheel through the wrapper, without changing Windows App Control.

## Guaranteed-exposure follow-up (study002)

The [protocol](docs/extension-study-002-protocol.md) and [completion report](docs/extension-study-002-completion-report.md) preserve the prior limited-exposure null unchanged. This additive follow-up completed240 fixed pilot units,5,040 full real-model E5 units,600 planned real-model/scripted-thief joint opportunities and240 scripted attenuation units. The full archive has5880primary/5885raw units; all58,669protected original/001 paths are unchanged;236tests pass.

Full injected C0 baseline: coerced attempts445/900; committed harm432/900. Combined protected conditions committed0/2700coerced harms; per-condition counts, task completion, exposure, exact McNemar/Holm verdicts, attribution errors, confidence intervals and all nulls are in the report. These are synthetic controlled tasks, not general model rankings or production assurances. C3 includes authority enforcement and remains an experimental proof-of-possession profile. Stock Llama/Mistral pilot interfaces failed benign calibration; same-weight rendering fixes were disclosed before full freeze, without extra sampling or changed eligibility. The original pilot is not pooled with full collection.

One-command sealed reanalysis (source/evidence ZIP or checkout):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/reproduce_extension2.ps1
```

Fresh collection requires a Git checkout with the pushed`extension-study-002-freeze-v1`tag, ignored`.env`, Docker/NVIDIA, network access and the preserved`.runtime/spend.sqlite`ledger. Never reset that ledger to obtain a new budget:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/reproduce_extension2.ps1 -Mode Collect
```

[Markdown/LaTeX tables and figures](results/extension-study-002/publication), [pilot results](results/extension-study-002-pilot/analysis), [template amendment](docs/extension-study-002-amendments.md), [archive release](https://github.com/fT0ned/csec603-zero-trust-agent-simulation/releases/tag/extension-study-002), and [owner DOI steps](docs/extension-zenodo-steps.md). Global conservative ledgerUSD2.968440308; study002USD1.070321135. The paper was not edited.
