# Binding-response study: results

**Mechanism verification (configuration-determined, scripted attacker); not a hypothesis test. Repeats are near-deterministic.**

Collection: pilot phase, git commit 1964145957. 10 of 10 planned runs completed (0 failed or excluded attempts retained in raw data).

## What happened, in plain English

- **C1 short-lived ID (bearer)** (2 runs): the stolen token executed at least one attacker request in 2/2 runs (data export allowed 2/2, email to the attacker allowed 2/2); a committed attacker effect appears in the independent tool ledger in 2/2 runs (10 records exported by the attacker). Median seconds after theft until the probe was first refused: 271.686. The legitimate agent could still work right after the attack in 2/2 runs (reasons: {"valid": 2}).
- **C2 full Zero Trust (log only)** (2 runs): the stolen token executed at least one attacker request in 2/2 runs (data export allowed 2/2, email to the attacker allowed 0/2); a committed attacker effect appears in the independent tool ledger in 2/2 runs (10 records exported by the attacker). Median seconds after theft until the probe was first refused: 271.848. The legitimate agent could still work right after the attack in 2/2 runs (reasons: {"allowed": 2}).
- **C2-AS auto-suspend** (2 runs): the stolen token executed at least one attacker request in 0/2 runs (data export allowed 0/2, email to the attacker allowed 0/2); a committed attacker effect appears in the independent tool ledger in 0/2 runs (0 records exported by the attacker). Median seconds after theft until the probe was first refused: 0.071. Detection to containment: median 11.1 ms (n=2). The legitimate agent could still work right after the attack in 0/2 runs (reasons: {"suspended": 2}).
- **C3 key-bound credential** (2 runs): the stolen token executed at least one attacker request in 0/2 runs (data export allowed 0/2, email to the attacker allowed 0/2); a committed attacker effect appears in the independent tool ledger in 0/2 runs (0 records exported by the attacker). Median seconds after theft until the probe was first refused: 0.055. The legitimate agent could still work right after the attack in 2/2 runs (reasons: {"allowed": 2}).
- **C3-AS key-bound + auto-suspend** (2 runs): the stolen token executed at least one attacker request in 0/2 runs (data export allowed 0/2, email to the attacker allowed 0/2); a committed attacker effect appears in the independent tool ledger in 0/2 runs (0 records exported by the attacker). Median seconds after theft until the probe was first refused: 0.057. Detection to containment: median 3.4 ms (n=2). The legitimate agent could still work right after the attack in 0/2 runs (reasons: {"suspended": 2}).

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
| C1 | 271.686 | 271.686 | 271.79 | 0 | 266.72 |
| C2 | 271.848 | 271.848 | 271.864 | 0 | 266.84 |
| C2-AS | 0.071 | 0.071 | 0.093 | 0 | 0.0 |
| C3 | 0.055 | 0.055 | 0.057 | 0 | 0.0 |
| C3-AS | 0.057 | 0.057 | 0.07 | 0 | 0.0 |

## Table: detection to containment (AS conditions)

| Condition | n | Median ms | IQR ms | Min | Max |
|---|---|---|---|---|---|
| C2-AS | 2 | 11.09 | 8.19 to 13.99 | 5.29 | 16.88 |
| C3-AS | 2 | 3.39 | 3.15 to 3.63 | 2.91 | 3.86 |

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
| C2 | 2/2 | 2/2 | 120/120 | 10/10 |
| C2-AS | 2/2 | 2/2 | 12/12 | 10/10 |
| C3 | 2/2 | 2/2 | 12/12 | 10/10 |
| C3-AS | 2/2 | 2/2 | 12/12 | 10/10 |

## Table: latency of legitimate requests (descriptive; median of per-run medians, milliseconds)

| Condition | Gateway round trip | Client signing | PA authorization |
|---|---|---|---|
| C1 | 53.28 (IQR 51.24 to 55.31) | n/a | 0.00 (IQR 0.00 to 0.00) |
| C2 | 61.79 (IQR 60.64 to 62.94) | n/a | 4.64 (IQR 3.81 to 5.48) |
| C2-AS | 69.31 (IQR 64.86 to 73.76) | n/a | 4.18 (IQR 3.47 to 4.90) |
| C3 | 51.53 (IQR 50.53 to 52.53) | 8.93 (IQR 8.70 to 9.15) | 2.01 (IQR 1.91 to 2.11) |
| C3-AS | 46.11 (IQR 45.38 to 46.84) | 9.34 (IQR 9.10 to 9.58) | 1.68 (IQR 1.67 to 1.69) |

Difference of medians (round trip only, runs executed concurrently on one host): {"C3 minus C2": -10.262, "C3-AS minus C2-AS": -23.195}.

## Figures

- fig-attacker-success.svg
- fig-exposure-survival.svg
- fig-availability-cost.svg

Machine-readable: results.json, summary-table.csv, survival-km.csv, detection-to-containment.csv.
