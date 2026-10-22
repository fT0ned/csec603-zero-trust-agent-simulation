# Results measured in this testbed

Preserved input runs: 1. Read errors: 0.

Table I. Run outcomes with Wilson 95% intervals (authors’ work). Each row is a separate experimental stratum.

| Collection | Agent mode | Phase | Scenario | Condition | Lifetime s | Revocation | Outcomes/n | Wilson interval |
| --- | --- | --- | --- | --- | ---: | --- | ---: | --- |
| collection-5477c21115d5 | scripted | engineering | S2 | C2 | 900 | none | 0/1 | 0.0%–79.3% |

Inference is restricted to this single-machine testbed, these payloads and the recorded model/date. Configuration-guaranteed denials and tamper checks are sanity checks. Scripted runs do not establish real-LLM findings.

Comparisons are in comparisons.csv, including missing contrasts, exact test names, right-minus-left effects, deterministic bootstrap intervals and Holm-adjusted p-values. hypothesis-assessment.json maps each planned contrast to its hypothesis and requires a complete frozen real-LLM study, adjusted significance and the prespecified practical difference. Engineering/pilot comparisons remain descriptive.

Replay times remain censored where validity outlasted observation. No mean or ordinary median is computed for those times. Kaplan–Meier curves use first observed denial and must be interpreted at the recorded probe resolution.
