# Binding-response study: results

**Mechanism verification (configuration-determined, scripted attacker); not a hypothesis test. Repeats are near-deterministic.**

Collection: full phase, git commit 33f7f09de7. 150 of 150 planned runs completed (0 failed or excluded attempts retained in raw data).

## What happened, in plain English

- **C1 short-lived ID (bearer)** (30 runs): the stolen token executed at least one attacker request in 30/30 runs (data export allowed 30/30, email to the attacker allowed 30/30); a committed attacker effect appears in the independent tool ledger in 30/30 runs (150 records exported by the attacker). Median seconds after theft until the probe was first refused: 272.117. The legitimate agent could still work right after the attack in 30/30 runs (reasons: {"valid": 30}).
- **C2 full Zero Trust (log only)** (30 runs): the stolen token executed at least one attacker request in 30/30 runs (data export allowed 30/30, email to the attacker allowed 0/30); a committed attacker effect appears in the independent tool ledger in 30/30 runs (150 records exported by the attacker). Median seconds after theft until the probe was first refused: 272.152. The legitimate agent could still work right after the attack in 30/30 runs (reasons: {"allowed": 30}).
- **C2-AS auto-suspend** (30 runs): the stolen token executed at least one attacker request in 0/30 runs (data export allowed 0/30, email to the attacker allowed 0/30); a committed attacker effect appears in the independent tool ledger in 0/30 runs (0 records exported by the attacker). Median seconds after theft until the probe was first refused: 0.056. Detection to containment: median 2.3 ms (n=30). The legitimate agent could still work right after the attack in 0/30 runs (reasons: {"suspended": 30}).
- **C3 key-bound credential** (30 runs): the stolen token executed at least one attacker request in 0/30 runs (data export allowed 0/30, email to the attacker allowed 0/30); a committed attacker effect appears in the independent tool ledger in 0/30 runs (0 records exported by the attacker). Median seconds after theft until the probe was first refused: 0.062. The legitimate agent could still work right after the attack in 30/30 runs (reasons: {"allowed": 30}).
- **C3-AS key-bound + auto-suspend** (30 runs): the stolen token executed at least one attacker request in 0/30 runs (data export allowed 0/30, email to the attacker allowed 0/30); a committed attacker effect appears in the independent tool ledger in 0/30 runs (0 records exported by the attacker). Median seconds after theft until the probe was first refused: 0.064. Detection to containment: median 2.6 ms (n=30). The legitimate agent could still work right after the attack in 0/30 runs (reasons: {"suspended": 30}).

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
| C1 | 271.883 | 272.117 | 272.599 | 0 | 267.11 |
| C2 | 271.964 | 272.152 | 272.571 | 0 | 267.16 |
| C2-AS | 0.05 | 0.056 | 0.071 | 0 | 0.0 |
| C3 | 0.056 | 0.062 | 0.075 | 0 | 0.0 |
| C3-AS | 0.058 | 0.064 | 0.074 | 0 | 0.0 |

## Table: detection to containment (AS conditions)

| Condition | n | Median ms | IQR ms | Min | Max |
|---|---|---|---|---|---|
| C2-AS | 30 | 2.30 | 1.96 to 3.15 | 0.86 | 20.37 |
| C3-AS | 30 | 2.56 | 2.07 to 3.29 | 0.86 | 50.83 |

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
| C2 | 30/30 | 30/30 | 1800/1800 | 150/150 |
| C2-AS | 30/30 | 30/30 | 180/180 | 150/150 |
| C3 | 30/30 | 30/30 | 180/180 | 150/150 |
| C3-AS | 30/30 | 30/30 | 180/180 | 150/150 |

## Table: latency of legitimate requests (descriptive; median of per-run medians, milliseconds)

| Condition | Gateway round trip | Client signing | PA authorization |
|---|---|---|---|
| C1 | 55.83 (IQR 49.11 to 60.07) | n/a | 0.00 (IQR 0.00 to 0.00) |
| C2 | 54.84 (IQR 51.55 to 65.47) | n/a | 2.10 (IQR 1.81 to 2.41) |
| C2-AS | 49.97 (IQR 42.19 to 55.97) | n/a | 1.89 (IQR 1.61 to 2.29) |
| C3 | 54.88 (IQR 48.05 to 63.51) | 8.93 (IQR 7.72 to 9.44) | 1.96 (IQR 1.80 to 2.23) |
| C3-AS | 52.21 (IQR 48.93 to 60.51) | 8.76 (IQR 8.11 to 10.47) | 1.88 (IQR 1.65 to 2.13) |

Difference of medians (round trip only, runs executed concurrently on one host): {"C3 minus C2": 0.04, "C3-AS minus C2-AS": 2.245}.

## Figures

- fig-attacker-success.svg
- fig-exposure-survival.svg
- fig-availability-cost.svg

Machine-readable: results.json, summary-table.csv, survival-km.csv, detection-to-containment.csv.
