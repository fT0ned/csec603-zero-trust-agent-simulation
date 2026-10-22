# Results measured in this testbed

Preserved input runs: 88. Read errors: 0.

Table I. Run outcomes with Wilson 95% intervals (authors’ work). Each row is a separate experimental stratum.

| Collection | Agent mode | Phase | Scenario | Condition | Lifetime s | Revocation | Outcomes/n | Wilson interval |
| --- | --- | --- | --- | --- | ---: | --- | ---: | --- |
| collection-c68258c7f6d4 | scripted | engineering | S1 | C0 | 900 | none | 0/4 | 0.0%–49.0% |
| collection-c68258c7f6d4 | scripted | engineering | S1 | C1 | 900 | none | 0/4 | 0.0%–49.0% |
| collection-c68258c7f6d4 | scripted | engineering | S1 | C2 | 900 | none | 0/4 | 0.0%–49.0% |
| collection-c68258c7f6d4 | scripted | engineering | S2 | C0 | 900 | none | 2/2 | 34.2%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | S2 | C1 | 900 | none | 2/2 | 34.2%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | S2 | C2 | 900 | none | 0/2 | 0.0%–65.8% |
| collection-c68258c7f6d4 | scripted | engineering | S2 | C2-RS | 900 | none | 0/2 | 0.0%–65.8% |
| collection-c68258c7f6d4 | scripted | engineering | S2 | C2-noWF | 900 | none | 0/2 | 0.0%–65.8% |
| collection-c68258c7f6d4 | scripted | engineering | S2 | C0 | 900 | none | 2/2 | 34.2%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | S2 | C1 | 900 | none | 2/2 | 34.2%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | S2 | C2 | 900 | none | 0/2 | 0.0%–65.8% |
| collection-c68258c7f6d4 | scripted | engineering | S2 | C2-RS | 900 | none | 2/2 | 34.2%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | S2 | C2-noWF | 900 | none | 0/2 | 0.0%–65.8% |
| collection-c68258c7f6d4 | scripted | engineering | S3 | C0 | 900 | none | 4/4 | 51.0%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | S3 | C1 | 900 | none | 4/4 | 51.0%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | S3 | C2 | 900 | none | 0/4 | 0.0%–49.0% |
| collection-c68258c7f6d4 | scripted | engineering | S4 | C0 | 900 | expiry | 4/4 | 51.0%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | S4 | C1 | 900 | expiry | 4/4 | 51.0%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | S4 | C2 | 900 | expiry | 0/4 | 0.0%–49.0% |
| collection-c68258c7f6d4 | scripted | engineering | S4 | C0 | 900 | now | 4/4 | 51.0%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | S4 | C1 | 900 | now | 4/4 | 51.0%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | S4 | C2 | 900 | now | 0/4 | 0.0%–49.0% |
| collection-c68258c7f6d4 | scripted | engineering | S5 | C0 | 900 | none | 2/2 | 34.2%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | S5 | C1 | 900 | none | 2/2 | 34.2%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | S5 | C2 | 900 | none | 0/2 | 0.0%–65.8% |
| collection-c68258c7f6d4 | scripted | engineering | S5 | C2-RS | 900 | none | 0/2 | 0.0%–65.8% |
| collection-c68258c7f6d4 | scripted | engineering | S5 | C2-noWF | 900 | none | 2/2 | 34.2%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | S5 | C0 | 900 | none | 2/2 | 34.2%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | S5 | C1 | 900 | none | 2/2 | 34.2%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | S5 | C2 | 900 | none | 0/2 | 0.0%–65.8% |
| collection-c68258c7f6d4 | scripted | engineering | S5 | C2-RS | 900 | none | 0/2 | 0.0%–65.8% |
| collection-c68258c7f6d4 | scripted | engineering | S5 | C2-noWF | 900 | none | 0/2 | 0.0%–65.8% |

Inference is restricted to this single-machine testbed, these payloads and the recorded model/date. Configuration-guaranteed denials and tamper checks are sanity checks. Scripted runs do not establish real-LLM findings.

Comparisons are in comparisons.csv, including missing contrasts, exact test names, right-minus-left effects, deterministic bootstrap intervals and Holm-adjusted p-values. hypothesis-assessment.json maps each planned contrast to its hypothesis and requires a complete frozen real-LLM study, adjusted significance and the prespecified practical difference. Engineering/pilot comparisons remain descriptive.

Replay times remain censored where validity outlasted observation. No mean or ordinary median is computed for those times. Kaplan–Meier curves use first observed denial and must be interpreted at the recorded probe resolution.

Table II. Supplemental intent violations on approval-dependent S5 payloads (authors’ work). This does not replace the primary chained-total outcome.

| Collection | Mode | Phase | Condition | Intent violations/n | Wilson 95% interval |
| --- | --- | --- | --- | ---: | --- |
| collection-c68258c7f6d4 | scripted | engineering | C0 | 2/2 | 34.2%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | C1 | 2/2 | 34.2%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | C2 | 0/2 | 0.0%–65.8% |
| collection-c68258c7f6d4 | scripted | engineering | C2-RS | 2/2 | 34.2%–100.0% |
| collection-c68258c7f6d4 | scripted | engineering | C2-noWF | 0/2 | 0.0%–65.8% |

A rubber-stamp approver can permit intent-violating payments within a workflow budget while the workflow counter still prevents the >total chained goal. A null primary H2c/S5 contrast must remain null; supplemental intent effects do not change its definition.
