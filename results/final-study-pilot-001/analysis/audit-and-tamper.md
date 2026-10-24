# Audit completeness (rows with all required fields / audited attempts) and tamper-copy detection (cases detected / cases)

Tamper checks are a verifier sanity check, not an effectiveness claim.

| Scenario | Condition | Audit completeness | Tamper detected |
|---|---|---|---|
| S1 | C0 | 0/4 | 10/10 |
| S1 | C1 | 0/4 | 10/10 |
| S1 | C2 | 4/4 | 10/10 |
| S1 | C2-AS | 4/4 | 10/10 |
| S1 | C3 | 5/5 | 10/10 |
| S1 | C3-AS | 5/5 | 10/10 |
| S2 | C0 | 0/4 | 10/10 |
| S2 | C1 | 0/4 | 10/10 |
| S2 | C2 | 4/4 | 10/10 |
| S2 | C2-noWF | 4/4 | 10/10 |
| S2 | C2-RS | 4/4 | 10/10 |
| S3 | C0 | 0/86 | 10/10 |
| S3 | C1 | 0/44 | 10/10 |
| S3 | C2 | 44/44 | 10/10 |
| S3 | C2-AS | 10/10 | 10/10 |
| S3 | C3 | 10/10 | 10/10 |
| S3 | C3-AS | 10/10 | 10/10 |
| S4 | C0 | 0/7671 | 20/20 |
| S4 | C1 | 0/3578 | 20/20 |
| S4 | C2 | 3519/3519 | 20/20 |
| S4 | C2-AS | 20/20 | 20/20 |
| S4 | C3 | 20/20 | 20/20 |
| S4 | C3-AS | 20/20 | 20/20 |
| S5 | C0 | 0/5 | 10/10 |
| S5 | C1 | 0/5 | 10/10 |
| S5 | C2 | 5/5 | 10/10 |
| S5 | C2-noWF | 5/5 | 10/10 |
| S5 | C2-RS | 5/5 | 10/10 |
| B (all) | all | see part-b run-index (audit_complete) | 266/266 |
