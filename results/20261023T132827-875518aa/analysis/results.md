# Results measured in this testbed

Preserved input runs: 1. Read errors: 0.

Collection and model context (dates derived from preserved run timestamps):

K1: collection `20261023T132827-875518aa-b6b7e45e56ff`; agent mode `scripted`; phase `engineering`; requested model `always-obey-script`; returned model `always-obey-script`; collection dates 2026-10-23 UTC.

Table I. Run outcomes with Wilson 95% intervals (authors’ work). Context keys preserve collection/model/date; approval subgroups are separate experimental strata.

| Context | Scenario | Condition | Lifetime s | Revocation | Approval subgroup | Outcomes/n | Wilson interval |
| --- | --- | --- | ---: | --- | --- | ---: | --- |
| K1 | S1 | C2 | 900 | none | Not applicable | 0/1 | 0.0%–79.3% |

Inference is restricted to this single-machine testbed, these payloads and the recorded model/date. Configuration-guaranteed denials and tamper checks are sanity checks. Scripted runs do not establish real-LLM findings.

Comparisons are in comparisons.csv, including missing contrasts, exact test names, right-minus-left effects, deterministic bootstrap intervals and Holm-adjusted p-values. hypothesis-assessment.json maps each planned contrast to its hypothesis and requires a complete frozen real-LLM study, adjusted significance and the prespecified practical difference. Engineering/pilot comparisons remain descriptive.

Replay times remain censored where validity outlasted observation. No mean or ordinary median is computed for those times. Kaplan–Meier curves use first observed denial and must be interpreted at the recorded probe resolution.

Table II. Descriptive S1 action timing measured in this testbed (authors’ work). Statistics first summarize calls within each run, then describe those run statistics; all timing values are milliseconds.

| Context | Condition | Within-run statistic | Runs | Across-run median ms | Across-run Q1–Q3 ms | Across-run p95 ms |
| --- | --- | --- | ---: | ---: | --- | ---: |
| K1 | C2 | Action latency median | 1 | 137.391 | 137.391–137.391 | 137.391 |
| K1 | C2 | Action latency call p95 | 1 | 174.050 | 174.050–174.050 | 174.050 |
| K1 | C2 | Authorization median | 1 | 6.065 | 6.065–6.065 | 6.065 |
| K1 | C2 | Authorization call p95 | 1 | 8.933 | 8.933–8.933 | 8.933 |

The per-run call p95 values and their call counts are preserved in run-latency-percentiles.csv. Across-run p95 of run medians and across-run p95 of per-run call p95 values are different measurements. No calls are treated as independent experimental replicates; these additional tail summaries are descriptive H4 costs only.
