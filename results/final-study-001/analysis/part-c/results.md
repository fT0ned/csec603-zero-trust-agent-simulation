# Binding-response study: results

**Mechanism verification (configuration-determined, scripted attacker); not a hypothesis test. Repeats are near-deterministic.**

Collection: full phase, git commit fedd511bb2. 150 of 150 planned runs completed (0 failed or excluded attempts retained in raw data).

## What happened, in plain English

- **C1 short-lived ID (bearer)** (30 runs): the stolen token executed at least one attacker request in 30/30 runs (data export allowed 30/30, email to the attacker allowed 30/30); a committed attacker effect appears in the independent tool ledger in 30/30 runs (150 records exported by the attacker). Median seconds after theft until the probe was first refused: 242.417. The legitimate agent could still work right after the attack in 30/30 runs (reasons: {"valid": 30}).
- **C2 full Zero Trust (log only)** (30 runs): the stolen token executed at least one attacker request in 30/30 runs (data export allowed 30/30, email to the attacker allowed 0/30); a committed attacker effect appears in the independent tool ledger in 30/30 runs (150 records exported by the attacker). Median seconds after theft until the probe was first refused: 242.451. The legitimate agent could still work right after the attack in 30/30 runs (reasons: {"allowed": 30}).
- **C2-AS auto-suspend** (30 runs): the stolen token executed at least one attacker request in 0/30 runs (data export allowed 0/30, email to the attacker allowed 0/30); a committed attacker effect appears in the independent tool ledger in 0/30 runs (0 records exported by the attacker). Median seconds after theft until the probe was first refused: 0.069. Detection to containment: median 2.3 ms (n=30). The legitimate agent could still work right after the attack in 0/30 runs (reasons: {"suspended": 30}).
- **C3 key-bound credential** (30 runs): the stolen token executed at least one attacker request in 0/30 runs (data export allowed 0/30, email to the attacker allowed 0/30); a committed attacker effect appears in the independent tool ledger in 0/30 runs (0 records exported by the attacker). Median seconds after theft until the probe was first refused: 0.082. The legitimate agent could still work right after the attack in 30/30 runs (reasons: {"allowed": 30}).
- **C3-AS key-bound + auto-suspend** (30 runs): the stolen token executed at least one attacker request in 0/30 runs (data export allowed 0/30, email to the attacker allowed 0/30); a committed attacker effect appears in the independent tool ledger in 0/30 runs (0 records exported by the attacker). Median seconds after theft until the probe was first refused: 0.063. Detection to containment: median 2.3 ms (n=30). The legitimate agent could still work right after the attack in 0/30 runs (reasons: {"suspended": 30}).

## Table: stolen-token outcomes (counts with Wilson 95% intervals)

| Condition | Any attacker request executed | Data export allowed | Email to attacker allowed | Effect in tool ledger |
|---|---|---|---|---|
| C1 | 30/30 [0.89, 1.00] | 30/30 [0.89, 1.00] | 30/30 [0.89, 1.00] | 30/30 [0.89, 1.00] |
| C2 | 30/30 [0.89, 1.00] | 30/30 [0.89, 1.00] | 0/30 [0.00, 0.11] | 30/30 [0.89, 1.00] |
| C2-AS | 0/30 [0.00, 0.11] | 0/30 [0.00, 0.11] | 0/30 [0.00, 0.11] | 0/30 [0.00, 0.11] |
| C3 | 0/30 [0.00, 0.11] | 0/30 [0.00, 0.11] | 0/30 [0.00, 0.11] | 0/30 [0.00, 0.11] |
| C3-AS | 0/30 [0.00, 0.11] | 0/30 [0.00, 0.11] | 0/30 [0.00, 0.11] | 0/30 [0.00, 0.11] |

## Table: exposure (seconds after theft until the harmless probe is first refused)

Kaplan-Meier handling: runs where the probe was never refused before the window ended are right-censored and never averaged; quantiles not reached are reported as "> window".

| Condition | Q25 | Median | Q75 | Censored runs | Last successful attacker request, median (lower bound if censored) |
|---|---|---|---|---|---|
| C1 | 242.182 | 242.417 | 242.668 | 0 | 237.4 |
| C2 | 242.28 | 242.451 | 242.651 | 0 | 237.44 |
| C2-AS | 0.059 | 0.069 | 0.087 | 0 | 0.0 |
| C3 | 0.07 | 0.082 | 0.096 | 0 | 0.0 |
| C3-AS | 0.051 | 0.063 | 0.08 | 0 | 0.0 |

## Table: detection to containment (AS conditions)

| Condition | n | Median ms | IQR ms | Min | Max |
|---|---|---|---|---|---|
| C2-AS | 30 | 2.25 | 1.95 to 2.75 | 0.97 | 4.98 |
| C3-AS | 30 | 2.26 | 2.02 to 2.66 | 0.91 | 11.03 |

## Table: availability cost (legitimate agent right after the attack burst)

| Condition | Legitimate task completed before theft | Legitimate request allowed after attack | Reasons when denied |
|---|---|---|---|
| C1 | 30/30 | 30/30 | {"valid": 30} |
| C2 | 30/30 | 30/30 | {"allowed": 30} |
| C2-AS | 30/30 | 0/30 | {"suspended": 30} |
| C3 | 30/30 | 30/30 | {"allowed": 30} |
| C3-AS | 30/30 | 0/30 | {"suspended": 30} |

## Table: audit evidence

| Condition | Audit chain valid | Audit flags impersonation | Full C2 fields in rows | Tamper cases detected |
|---|---|---|---|---|
| C1 | 30/30 | n/a | n/a | 150/150 |
| C2 | 30/30 | 30/30 | 1623/1623 | 150/150 |
| C2-AS | 30/30 | 30/30 | 184/184 | 150/150 |
| C3 | 30/30 | 30/30 | 183/183 | 150/150 |
| C3-AS | 30/30 | 30/30 | 183/183 | 150/150 |

## Table: latency of legitimate requests (descriptive; median of per-run medians, milliseconds)

| Condition | Gateway round trip | Client signing | PA authorization |
|---|---|---|---|
| C1 | 67.47 (IQR 61.71 to 77.00) | n/a | 0.00 (IQR 0.00 to 0.00) |
| C2 | 64.84 (IQR 52.18 to 72.30) | n/a | 1.94 (IQR 1.81 to 2.24) |
| C2-AS | 56.68 (IQR 45.55 to 64.83) | n/a | 1.68 (IQR 1.59 to 1.90) |
| C3 | 66.58 (IQR 56.05 to 71.32) | 8.46 (IQR 7.92 to 9.35) | 1.96 (IQR 1.80 to 2.17) |
| C3-AS | 51.31 (IQR 47.17 to 65.43) | 8.08 (IQR 7.61 to 8.75) | 1.62 (IQR 1.57 to 1.76) |

Difference of medians (round trip only, runs executed concurrently on one host): {"C3 minus C2": 1.732, "C3-AS minus C2-AS": -5.366}.

## Figures

- fig-attacker-success.svg
- fig-exposure-survival.svg
- fig-availability-cost.svg

Machine-readable: results.json, summary-table.csv, survival-km.csv, detection-to-containment.csv.
