# Recommendation matrix linked to results

Measured support is separated from architectural rationale; see evidence class.

| Recommendation | Result it rests on | Evidence class | Where |
|---|---|---|---|
| Use short-lived attested identity with revocation | C1/C2 bound replay exposure to the credential lifetime (S3 table); a static key is never denied within the window | mechanism verification | comparative-analysis.md, part-a/replay-survival.svg |
| Add per-action policy and workflow limits | S2 unauthorized outcome C0 0/2 (0.0%; 95% CI 0.0-65.8%) vs C2 0/2 (0.0%; 95% CI 0.0-65.8%); S5 workflow ablation in results-table.md | measured behaviour + policy-determined | results-table.md, h-verdicts.md |
| Bind credentials to a sender key (C3) | Stolen bearer token executed 0 requests when the proof was required (Part C, Part A S3/S4 tables) | mechanism verification | part-c/results.md |
| Auto-suspend on origin mismatch (AS) only with availability planning | Contains within milliseconds but suspends the legitimate agent (availability-cost.md) | mechanism verification + descriptive cost | availability-cost.md |
| Keep approval careful, not rubber-stamp | C2-RS vs C2 in S2/S5 and Part B A3 | measured behaviour | h-verdicts.md, part-b/paired-contrasts.csv |
| Protect audit checkpoints | Alterations detected in all tamper copies; audit completeness table | mechanism verification | audit-and-tamper.md |
