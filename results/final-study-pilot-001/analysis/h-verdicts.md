# Hypothesis verdicts with evidence class

Support claims require eligibility (complete frozen real-LLM collection). Eligible: **False**.

| Hypothesis | Part | Evidence class | Verdict | Note |
|---|---|---|---|---|
| H1 | A | mechanism verification (configuration-determined; counts + Wilson CI, no p-value claim) | Descriptive only: 2 | Per-contrast detail in part-a/hypothesis-assessment.json; strata are not pooled. |
| H1b | A | mechanism verification (configuration-determined; counts + Wilson CI, no p-value claim) | Descriptive only: 3; Not measured: 3 | Per-contrast detail in part-a/hypothesis-assessment.json; strata are not pooled. |
| H2 | A | measured behaviour (outcome can vary with model behaviour) | Descriptive only: 12 | Per-contrast detail in part-a/hypothesis-assessment.json; strata are not pooled. |
| H2b | A | measured behaviour (outcome can vary with model behaviour) | Descriptive only: 2 | Per-contrast detail in part-a/hypothesis-assessment.json; strata are not pooled. |
| H2c | A | measured behaviour (outcome can vary with model behaviour) | Descriptive only: 2 | Per-contrast detail in part-a/hypothesis-assessment.json; strata are not pooled. |
| H3 | A | mechanism verification (configuration-determined; counts + Wilson CI, no p-value claim) | Descriptive only: 6 | Per-contrast detail in part-a/hypothesis-assessment.json; strata are not pooled. |
| H3b | A | mechanism verification (configuration-determined; counts + Wilson CI, no p-value claim) | Sanity check passed: 340/340 altered audit copies detected (Part A) | Per-contrast detail in part-a/hypothesis-assessment.json; strata are not pooled. |
| H4 | A | descriptive | Descriptive only (see latency/overhead tables) | Per-contrast detail in part-a/hypothesis-assessment.json; strata are not pooled. |
| A1 | B | measured behaviour (outcome can vary with model behaviour); C2 side policy-determined | descriptive-only: 8 | Exact McNemar with Holm over the family of 10; near-deterministic repeats (effective n < 30). |
| A2 | B | measured behaviour (outcome can vary with model behaviour); C2 side policy-determined | descriptive-only: 1 | Exact McNemar with Holm over the family of 10; near-deterministic repeats (effective n < 30). |
| A3 | B | measured behaviour (outcome can vary with model behaviour); C2 side policy-determined | descriptive-only: 1 | Exact McNemar with Holm over the family of 10; near-deterministic repeats (effective n < 30). |
| B1 | A+C | mechanism verification (configuration-determined; counts + Wilson CI, no p-value claim) | C1: attacker request executed 2/2, ledger effect 2/2; C2: attacker request executed 2/2, ledger effect 2/2; C2-AS: attacker request executed 0/2, ledger effect 0/2; C3: attacker request executed 0/2, ledger effect 0/2; C3-AS: attacker request executed 0/2, ledger effect 0/2 | Counts only; scripted attacker; no p-values. |
| B2 | C (+A S3/S4, B positives) | descriptive | C1: legit available after attack 2/2; C2: legit available after attack 2/2; C2-AS: legit available after attack 0/2; C3: legit available after attack 2/2; C3-AS: legit available after attack 0/2 | Availability cost of auto-suspend; C3 signing overhead in latency table. |
