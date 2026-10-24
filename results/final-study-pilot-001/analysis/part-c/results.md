# Binding-response study: results

**Mechanism verification (configuration-determined, scripted attacker); not a hypothesis test. Repeats are near-deterministic.**

Collection: pilot phase, git commit 6b7174ec54. 10 of 10 planned runs completed (0 failed or excluded attempts retained in raw data).

## What happened, in plain English

- **C1 short-lived ID (bearer)** (2 runs): the stolen token executed at least one attacker request in 2/2 runs (data export allowed 2/2, email to the attacker allowed 2/2); a committed attacker effect appears in the independent tool ledger in 2/2 runs (10 records exported by the attacker). Median seconds after theft until the probe was first refused: 240.31. The legitimate agent could still work right after the attack in 2/2 runs (reasons: {"valid": 2}).
- **C2 full Zero Trust (log only)** (2 runs): the stolen token executed at least one attacker request in 2/2 runs (data export allowed 2/2, email to the attacker allowed 0/2); a committed attacker effect appears in the independent tool ledger in 2/2 runs (10 records exported by the attacker). Median seconds after theft until the probe was first refused: 240.16. The legitimate agent could still work right after the attack in 2/2 runs (reasons: {"allowed": 2}).
- **C2-AS auto-suspend** (2 runs): the stolen token executed at least one attacker request in 0/2 runs (data export allowed 0/2, email to the attacker allowed 0/2); a committed attacker effect appears in the independent tool ledger in 0/2 runs (0 records exported by the attacker). Median seconds after theft until the probe was first refused: 0.118. Detection to containment: median 6.0 ms (n=2). The legitimate agent could still work right after the attack in 0/2 runs (reasons: {"suspended": 2}).
- **C3 key-bound credential** (2 runs): the stolen token executed at least one attacker request in 0/2 runs (data export allowed 0/2, email to the attacker allowed 0/2); a committed attacker effect appears in the independent tool ledger in 0/2 runs (0 records exported by the attacker). Median seconds after theft until the probe was first refused: 0.15. The legitimate agent could still work right after the attack in 2/2 runs (reasons: {"allowed": 2}).
- **C3-AS key-bound + auto-suspend** (2 runs): the stolen token executed at least one attacker request in 0/2 runs (data export allowed 0/2, email to the attacker allowed 0/2); a committed attacker effect appears in the independent tool ledger in 0/2 runs (0 records exported by the attacker). Median seconds after theft until the probe was first refused: 0.061. Detection to containment: median 17.0 ms (n=2). The legitimate agent could still work right after the attack in 0/2 runs (reasons: {"suspended": 2}).

## Table: stolen-token outcomes (counts with Wilson 95% intervals)

| Condition | Any attacker request executed | Data export allowed | Email to attacker allowed | Effect in tool ledger |
|---|---|---|---|---|
| C1 | 2/2 [0.34, 1.00] | 2/2 [0.34, 1.00] | 2/2 [0.34, 1.00] | 2/2 [0.34, 1.00] |
| C2 | 2/2 [0.34, 1.00] | 2/2 [0.34, 1.00] | 0/2 [0.00, 0.66] | 2/2 [0.34, 1.00] |
| C2-AS | 0/2 [0.00, 0.66] | 0/2 [0.00, 0.66] | 0/2 [0.00, 0.66] | 0/2 [0.00, 0.66] |
| C3 | 0/2 [0.00, 0.66] | 0/2 [0.00, 0.66] | 0/2 [0.00, 0.66] | 0/2 [0.00, 0.66] |
| C3-AS | 0/2 [0.00, 0.66] | 0/2 [0.00, 0.66] | 0/2 [0.00, 0.66] | 0/2 [0.00, 0.66] |

## Table: exposure (seconds after theft until the harmless probe is first refused)

Kaplan-Meier handling: runs where the probe was never refused before the window ended are right-censored and never averaged; quantiles not reached are reported as "> window".

| Condition | Q25 | Median | Q75 | Censored runs | Last successful attacker request, median (lower bound if censored) |
|---|---|---|---|---|---|
| C1 | 240.31 | 240.31 | 243.188 | 0 | 236.73 |
| C2 | 240.16 | 240.16 | 240.161 | 0 | 235.14 |
| C2-AS | 0.118 | 0.118 | 0.201 | 0 | 0.0 |
| C3 | 0.15 | 0.15 | 0.171 | 0 | 0.0 |
| C3-AS | 0.061 | 0.061 | 0.239 | 0 | 0.0 |

## Table: detection to containment (AS conditions)

| Condition | n | Median ms | IQR ms | Min | Max |
|---|---|---|---|---|---|
| C2-AS | 2 | 5.98 | 5.74 to 6.22 | 5.50 | 6.46 |
| C3-AS | 2 | 17.01 | 9.44 to 24.58 | 1.88 | 32.15 |

## Table: availability cost (legitimate agent right after the attack burst)

| Condition | Legitimate task completed before theft | Legitimate request allowed after attack | Reasons when denied |
|---|---|---|---|
| C1 | 2/2 | 2/2 | {"valid": 2} |
| C2 | 2/2 | 2/2 | {"allowed": 2} |
| C2-AS | 2/2 | 0/2 | {"suspended": 2} |
| C3 | 2/2 | 2/2 | {"allowed": 2} |
| C3-AS | 2/2 | 0/2 | {"suspended": 2} |

## Table: audit evidence

| Condition | Audit chain valid | Audit flags impersonation | Full C2 fields in rows | Tamper cases detected |
|---|---|---|---|---|
| C1 | 2/2 | n/a | n/a | 10/10 |
| C2 | 2/2 | 2/2 | 106/106 | 10/10 |
| C2-AS | 2/2 | 2/2 | 12/12 | 10/10 |
| C3 | 2/2 | 2/2 | 13/13 | 10/10 |
| C3-AS | 2/2 | 2/2 | 13/13 | 10/10 |

## Table: latency of legitimate requests (descriptive; median of per-run medians, milliseconds)

| Condition | Gateway round trip | Client signing | PA authorization |
|---|---|---|---|
| C1 | 82.72 (IQR 75.28 to 90.16) | n/a | 0.00 (IQR 0.00 to 0.00) |
| C2 | 84.36 (IQR 77.44 to 91.28) | n/a | 3.51 (IQR 3.30 to 3.71) |
| C2-AS | 48.51 (IQR 45.54 to 51.49) | n/a | 1.92 (IQR 1.86 to 1.97) |
| C3 | 57.58 (IQR 51.03 to 64.13) | 10.03 (IQR 9.05 to 11.02) | 2.36 (IQR 2.17 to 2.55) |
| C3-AS | 56.99 (IQR 53.52 to 60.46) | 10.61 (IQR 9.84 to 11.38) | 1.92 (IQR 1.80 to 2.04) |

Difference of medians (round trip only, runs executed concurrently on one host): {"C3 minus C2": -26.779, "C3-AS minus C2-AS": 8.475}.

## Figures

- fig-attacker-success.svg
- fig-exposure-survival.svg
- fig-availability-cost.svg

Machine-readable: results.json, summary-table.csv, survival-km.csv, detection-to-containment.csv.
