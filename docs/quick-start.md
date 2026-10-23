# Run your own experiment

## Open it

1. Start **Docker Desktop** and wait until it is ready.
2. Open PowerShell in `Phase2/GithubRepoLive` and run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/launch.ps1
   ```

3. Open **http://127.0.0.1:8765**. Leave Docker and the launch terminal open.

Your existing installation and credentials are already configured. On a new computer, follow [setup](runbook.md) first.

## Try a quick, free comparison

1. Choose **Engineering control checks**, then **Load preset**.
2. Keep **Scripted**, **Engineering verification**, **C0, C1, C2**, and **S1, S2, S5**. Set **Trials per cell = 1** and **Concurrency = 1**.
3. Click **Start experiment**. Select the new entry in **Collection history** to follow it.
4. Read **Compare conditions**, then select a trial and its action/policy/audit traces. Download **CSV**, **JSON**, or the **Reproducibility bundle**.
5. **Reset console** clears your selection; it keeps the results. Use **Cancel collection** to stop a dashboard-started run, retaining partial evidence.

Scripted mode deliberately attempts the attacks and makes no paid LLM calls. For actual model behavior, load **Exploratory neutral-prompt pilot** instead. It uses the provider and costs credit; start with one trial per cell. A model that never attempts an unauthorized action does not demonstrate that a security control stopped it.

## What to change

| Setting | Plain-English meaning |
| --- | --- |
| C0 / C1 / C2 | Broad static key / authenticated short-lived identity / identity plus Zero Trust controls. Keep all three for a fair comparison. |
| C2-noWF / C2-RS | Separately remove the workflow limit / use an always-approving reviewer. These isolate controls; use S2/S5. |
| S1 / S2 / S3 / S4 / S5 | Normal work / coerced agent / stolen credential / revocation / chained actions. |
| Trials per cell | Repetitions of each selected combination. More improves precision and takes longer. |
| Matched seed | Chooses a repeatable task/payload order. Keep it equal when comparing conditions. |
| Concurrency | How many trials run together. Keep it fixed for performance comparisons. |
| System prompt profile | Choose **Neutral v1** for new exploratory LLM tests. Use the same prompt across C0/C1/C2. |
| Timing, provider, and budget | Advanced settings: lifetimes, observation time, probe spacing, revocation, model and batch cost cap. |

S3/S4 use real time: a 3,600-second lifetime can take over an hour. C0's static key does not expire. Engineering timing is a short control check, not a lifetime study. Changing the model requires its credentials and a separately documented pilot. The batch cap cannot bypass the existing **$4 total spending limit**; the spending ledger must be preserved.

Dashboard changes apply to the **new batch**; its configuration is saved with its results under `results/<batch-id>/`. Old results and frozen studies stay separate. Use **Pilot** or **Engineering verification** for experiments while exploring. **Full frozen study** requires a new reviewed protocol/freeze; changing its settings alone does not create a valid confirmatory experiment.

## Change the tasks or security rules

These require code changes and another verification/freeze, rather than dashboard settings:

- Presets: `configs/*.json`.
- Tasks and attack examples: `testbed/fixtures.py`.
- Agent prompts and model interaction: `testbed/prompts.py`, `testbed/fixtures.py` and `testbed/agent.py`.
- Security decisions: `infra/opa/policy.rego` and `testbed/service.py`.
- Charts/statistics: `analysis/` and `scripts/plot_enforcement.py`.

Make a separate copy/protocol, keep tasks and agent instructions identical across conditions, and test before collecting new research. Never edit the preserved `study-002` or repair records, reuse their output folders, or move their freeze tags. For exact commands and deeper customization, use the [numbered runbook](runbook.md). For the completed findings and remaining paper work, use the [handoff](handoff.md).
