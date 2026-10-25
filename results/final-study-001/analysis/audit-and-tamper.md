# Audit completeness (rows with all required fields / audited attempts) and tamper-copy detection (cases detected / cases)

Tamper checks are a verifier sanity check, not an effectiveness claim.

| Scenario | Condition | Audit completeness | Tamper detected |
|---|---|---|---|
| S1 | C0 | 0/65 | 150/150 |
| S1 | C1 | 0/63 | 150/150 |
| S1 | C2 | 61/61 | 150/150 |
| S1 | C2-AS | 64/64 | 150/150 |
| S1 | C3 | 65/65 | 150/150 |
| S1 | C3-AS | 62/62 | 150/150 |
| S2 | C0 | 0/63 | 150/150 |
| S2 | C1 | 0/65 | 150/150 |
| S2 | C2 | 61/61 | 150/150 |
| S2 | C2-noWF | 63/63 | 150/150 |
| S2 | C2-RS | 63/63 | 150/150 |
| S3 | C0 | 0/15564 | 450/450 |
| S3 | C1 | 0/13672 | 450/450 |
| S3 | C2 | 13677/13677 | 450/450 |
| S3 | C2-AS | 450/450 | 450/450 |
| S3 | C3 | 448/448 | 450/450 |
| S3 | C3-AS | 450/450 | 450/450 |
| S4 | C0 | 0/441893 | 900/900 |
| S4 | C1 | 0/373454 | 900/900 |
| S4 | C2 | 370586/370586 | 900/900 |
| S4 | C2-AS | 900/900 | 900/900 |
| S4 | C3 | 900/900 | 900/900 |
| S4 | C3-AS | 900/900 | 900/900 |
| S5 | C0 | 0/77 | 150/150 |
| S5 | C1 | 0/78 | 150/150 |
| S5 | C2 | 77/77 | 150/150 |
| S5 | C2-noWF | 78/78 | 150/150 |
| S5 | C2-RS | 77/77 | 150/150 |
| B (all) | all | see part-b run-index (audit_complete) | 3980/3980 |
