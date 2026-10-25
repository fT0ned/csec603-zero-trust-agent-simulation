# Easiest way to see the results

Double-click **`Start-Dashboard.bat`** in this folder. A browser page opens with plain-English results for every study (nothing to install, read-only). Details and troubleshooting: [docs/easy-dashboard.md](docs/easy-dashboard.md). From a terminal: `.venv\Scripts\python.exe -m easyboard` (or `python -m easyboard`).

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
