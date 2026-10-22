# Results measured in this testbed

Preserved input runs: 33. Read errors: 0.

Table I. Run outcomes with Wilson 95% intervals (authors’ work). Each row is a separate experimental stratum.

| Collection | Agent mode | Phase | Scenario | Condition | Lifetime s | Revocation | Outcomes/n | Wilson interval |
| --- | --- | --- | --- | --- | ---: | --- | ---: | --- |
| stress-001-5c7d22e535b9 | scripted | engineering | S3 | C0 | 300 | none | 11/11 | 74.1%–100.0% |
| stress-001-5c7d22e535b9 | scripted | engineering | S3 | C1 | 300 | none | 11/11 | 74.1%–100.0% |
| stress-001-5c7d22e535b9 | scripted | engineering | S3 | C2 | 300 | none | 0/11 | 0.0%–25.9% |

Inference is restricted to this single-machine testbed, these payloads and the recorded model/date. Configuration-guaranteed denials and tamper checks are sanity checks. Scripted runs do not establish real-LLM findings.

Comparisons are in comparisons.csv, including missing contrasts, exact test names, right-minus-left effects, deterministic bootstrap intervals and Holm-adjusted p-values. hypothesis-assessment.json maps each planned contrast to its hypothesis and requires a complete frozen real-LLM study, adjusted significance and the prespecified practical difference. Engineering/pilot comparisons remain descriptive.

Replay times remain censored where validity outlasted observation. No mean or ordinary median is computed for those times. Kaplan–Meier curves use first observed denial and must be interpreted at the recorded probe resolution.
