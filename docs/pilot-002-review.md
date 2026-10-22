# Final pilot collection review

The real-LLM `pilot-002` collection completed 88/88 planned trials. Read-only validation passed with 1108 sealed raw files checked, no infrastructure reruns, no provider/model error runs, and no validation errors or warnings. All 88 recorded task outcomes were completed. These are pilot measurements in this single-machine testbed, not full-study hypothesis findings.

The preserved configuration uses `deepseek-flash`, four repeats per cell, concurrency 32, a 120-second scheduled credential handoff, 300-second replay/revocation credentials and a 305-second observation window. Other scenarios retain the 900-second main lifetime. S3 probes use 10 seconds and S4 probes 0.1 seconds. All returned model labels were `deepseek-flash`; this mutable alias is not an immutable model snapshot. Collection dates in the preserved timestamps are 2026-10-22 UTC.

The largest absolute error in the recorded theft-schedule timestamp was 1.448 ms. This is the harness schedule error, not a claim about remote receipt latency. The verifier detected 440/440 deliberately altered audit copies; this validates the tamper-check procedure as a sanity check.

Injection-follow counts were 0/20 in S2 and 0/20 in S5. The model's refusal to follow these payloads limits what the pilot can reveal about differences between enforcement conditions. Zero unauthorized outcomes cannot be credited solely to the controls. Approval-dependent and other payload strata contain only two trials per condition in this pilot; a zero-of-two Wilson 95% interval still reaches approximately 65.8%. Pilot comparisons remain descriptive regardless of their p-values.

The computed token charge was USD 0.02468220, with USD 0.00000000 in uncertain request reservations for this collection. Run cost records label their rate basis; account-balance/invoice reconciliation remains a separate check. The complete study must retain its own pre-run freeze, full manifest, budget gate and genuine measured results. No pilot observation is substituted for a full-study cell.

The regenerated [results table](../results/pilot-002/analysis/results.md) identifies model/date context and approval subgroups explicitly. [Validation](../results/pilot-002/validation.json), [hypothesis assessments](../results/pilot-002/analysis/hypothesis-assessment.json), [raw-file verification](../results/pilot-002/analysis/raw-verification.json), and [metric CSV](../results/pilot-002/analysis/metrics.csv) preserve the detailed checks and denominators.

Source byte hashes:

- `validation.json`: `38120e9c69f2d0bacfaeea937a0768c2f6b3a6e8b212ad75510641236d4787a4`
- `manifest.json`: `655c47a8722c81c88508e78145ce83a405cc4da3aeb2232263b97ffd620b07c5`
- `config.json`: `1d6423c1ea6ed983d0fe648f0eac2e6ce6bd347dace306dff4a8b0b65ef6eaa8`
