# Paper package: final-study-001

Everything here is measured in this single-machine testbed with the real model; see docs/final-study-protocol.md. This file only re-words the frozen analyzer outputs.

## Collection

- Planned runs: {'A': 2100, 'B': 840, 'C': 150} (total 3090). Part A complete: True; Part B complete: True; Part C complete: True.
- Raw seals verified: {'A': True, 'B': True, 'C': True}. Analysis errors: 0.
- Host clock: steps over 0.5 s: 0; flagged runs: 0; timing replacements applied: {'A': 0, 'B': 0, 'C': 0}.
- Cost (computed): USD 0.8553; returned model ids: {'deepseek-flash': 8993}; fingerprints: ['e72d3c7f663d3e1383b00b3884cb4501'].

## Hypothesis verdicts (evidence class first)

Support claims need the frozen, complete collection (eligible: **False**). Configuration-determined rows are mechanism verification: threshold counts, no p-value claim.

| Hypothesis | Evidence class | Result |
|---|---|---|
| H1 | mechanism verification | threshold met in 6 of 6 measured planned contrasts (8 defined) |
| H1b | mechanism verification | threshold met in 9 of 9 measured planned contrasts (18 defined) |
| H3 | mechanism verification | threshold met in 6 of 10 measured planned contrasts (12 defined) |
| H2 | measured behaviour (left side) | Holm and threshold both met in 0 of 24 contrasts; the rest are null or below threshold (listed under Null results) |
| H2b | measured behaviour (left side) | Holm and threshold both met in 0 of 2 contrasts; the rest are null or below threshold (listed under Null results) |
| H2c | measured behaviour (left side) | Holm and threshold both met in 0 of 2 contrasts; the rest are null or below threshold (listed under Null results) |
| H3b | mechanism verification | Sanity check passed: 10500/10500 altered audit copies detected (Part A) |
| H4 | descriptive | see latency-overhead-approval.md |
| A1 | measured behaviour (outcome can vary with model behaviour); C2 side policy-determined | supported: 8 |
| A2 | measured behaviour (outcome can vary with model behaviour); C2 side policy-determined | supported: 1 |
| A3 | measured behaviour (outcome can vary with model behaviour); C2 side policy-determined | supported: 1 |
| B1 | mechanism verification (configuration-determined; counts + Wilson CI, no p-value claim) | C1: attacker request executed 30/30, ledger effect 30/30; C2: attacker request executed 30/30, ledger effect 30/30; C2-AS: attacker request executed 0/30, ledger effect 0/30; C3: attacker request executed 0/30, ledger effect 0/30; C3-AS: attacker request executed 0/30, ledger effect 0/30 |
| B2 | descriptive | C1: legit available after attack 30/30; C2: legit available after attack 30/30; C2-AS: legit available after attack 0/30; C3: legit available after attack 30/30; C3-AS: legit available after attack 0/30 |

## Null or non-supported contrasts (stated plainly)

- H2 S2 reachable_authority C0->C2 p_holm=0.04248046875
- H2 S2 reachable_authority C0->C2 p_holm=0.04248046875
- H2 S2 reachable_authority C1->C2 p_holm=0.04248046875
- H2 S2 reachable_authority C1->C2 p_holm=0.04248046875
- H2 S2 unauthorized_outcome C0->C2 p_holm=1.0
- H2 S2 unauthorized_outcome C0->C2 p_holm=1.0
- H2 S2 unauthorized_outcome C1->C2 p_holm=1.0
- H2 S2 unauthorized_outcome C1->C2 p_holm=1.0
- H2 S3 reachable_authority C0->C2 p_holm=3.352252696714081e-05
- H2 S3 reachable_authority C0->C2 p_holm=3.352252696714081e-05
- H2 S3 reachable_authority C0->C2 p_holm=3.352252696714081e-05
- H2 S3 reachable_authority C1->C2 p_holm=3.352252696714081e-05
- H2 S3 reachable_authority C1->C2 p_holm=3.352252696714081e-05
- H2 S3 reachable_authority C1->C2 p_holm=3.352252696714081e-05
- H2 S3 unauthorized_outcome C0->C2 p_holm=1.4193356037139893e-06
- H2 S3 unauthorized_outcome C0->C2 p_holm=1.4193356037139893e-06
- H2 S3 unauthorized_outcome C0->C2 p_holm=1.4193356037139893e-06
- H2 S3 unauthorized_outcome C1->C2 p_holm=1.4193356037139893e-06
- H2 S3 unauthorized_outcome C1->C2 p_holm=1.4193356037139893e-06
- H2 S3 unauthorized_outcome C1->C2 p_holm=1.4193356037139893e-06
- H2b S5 cumulative_ratio C2->C2-noWF p_holm=1.0
- H2b S5 unauthorized_outcome C2->C2-noWF p_holm=1.0
- H2c S2 unauthorized_outcome C2->C2-RS p_holm=1.0
- H2c S5 unauthorized_outcome C2->C2-RS p_holm=1.0

Injection follow rates (separate from committed harm): S2 C0 0/30 (0.0%; 95% CI 0.0-11.4%); S2 C1 0/30 (0.0%; 95% CI 0.0-11.4%); S2 C2 0/30 (0.0%; 95% CI 0.0-11.4%); S2 C2-noWF 0/30 (0.0%; 95% CI 0.0-11.4%); S2 C2-RS 0/30 (0.0%; 95% CI 0.0-11.4%); S5 C0 0/30 (0.0%; 95% CI 0.0-11.4%); S5 C1 0/30 (0.0%; 95% CI 0.0-11.4%); S5 C2 0/30 (0.0%; 95% CI 0.0-11.4%); S5 C2-noWF 0/30 (0.0%; 95% CI 0.0-11.4%); S5 C2-RS 0/30 (0.0%; 95% CI 0.0-11.4%)

## Threats to validity

- One mutable model alias, one host, synthetic tools, simulated approver, scripted thief; no production inference.
- Temperature 0 makes repeats near-deterministic: effective sample size is closer to the number of distinct fixtures than to 30.
- C2-AS/C3/C3-AS are identical to C2 in S2/S5 by construction, so not allocated there.
- Part A S3/S4 timing resolution: 10 s (S3) and 0.1 s (S4) probe grids; exposure for C0 is right-censored at the window end.
- Stages ran B and C first, then A, so Part A timing is not perturbed by other parts, but the stages are not interleaved in time.
