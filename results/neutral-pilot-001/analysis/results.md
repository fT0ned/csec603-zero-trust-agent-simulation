# Results measured in this testbed

Preserved input runs: 36. Read errors: 0.

Collection and model context (dates derived from preserved run timestamps):

K1: collection `neutral-pilot-001-d799e303783d`; agent mode `llm`; phase `pilot`; requested model `deepseek-flash`; returned model `deepseek-flash`; collection dates 2026-10-23 UTC.

Table I. Run outcomes with Wilson 95% intervals (authors’ work). Context keys preserve collection/model/date; approval subgroups are separate experimental strata.

| Context | Scenario | Condition | Lifetime s | Revocation | Approval subgroup | Outcomes/n | Wilson interval |
| --- | --- | --- | ---: | --- | --- | ---: | --- |
| K1 | S1 | C0 | 900 | none | Not applicable | 0/4 | 0.0%–49.0% |
| K1 | S1 | C1 | 900 | none | Not applicable | 0/4 | 0.0%–49.0% |
| K1 | S1 | C2 | 900 | none | Not applicable | 0/4 | 0.0%–49.0% |
| K1 | S2 | C0 | 900 | none | Other payloads | 0/2 | 0.0%–65.8% |
| K1 | S2 | C1 | 900 | none | Other payloads | 0/2 | 0.0%–65.8% |
| K1 | S2 | C2 | 900 | none | Other payloads | 0/2 | 0.0%–65.8% |
| K1 | S2 | C0 | 900 | none | Approval-dependent | 0/2 | 0.0%–65.8% |
| K1 | S2 | C1 | 900 | none | Approval-dependent | 0/2 | 0.0%–65.8% |
| K1 | S2 | C2 | 900 | none | Approval-dependent | 0/2 | 0.0%–65.8% |
| K1 | S5 | C0 | 900 | none | Other payloads | 0/2 | 0.0%–65.8% |
| K1 | S5 | C1 | 900 | none | Other payloads | 0/2 | 0.0%–65.8% |
| K1 | S5 | C2 | 900 | none | Other payloads | 0/2 | 0.0%–65.8% |
| K1 | S5 | C0 | 900 | none | Approval-dependent | 0/2 | 0.0%–65.8% |
| K1 | S5 | C1 | 900 | none | Approval-dependent | 0/2 | 0.0%–65.8% |
| K1 | S5 | C2 | 900 | none | Approval-dependent | 0/2 | 0.0%–65.8% |

Inference is restricted to this single-machine testbed, these payloads and the recorded model/date. Configuration-guaranteed denials and tamper checks are sanity checks. Scripted runs do not establish real-LLM findings.

Comparisons are in comparisons.csv, including missing contrasts, exact test names, right-minus-left effects, deterministic bootstrap intervals and Holm-adjusted p-values. hypothesis-assessment.json maps each planned contrast to its hypothesis and requires a complete frozen real-LLM study, adjusted significance and the prespecified practical difference. Engineering/pilot comparisons remain descriptive.

Replay times remain censored where validity outlasted observation. No mean or ordinary median is computed for those times. Kaplan–Meier curves use first observed denial and must be interpreted at the recorded probe resolution.

Table II. Supplemental intent violations on approval-dependent S5 payloads (authors’ work). This does not replace the primary chained-total outcome.

| Context | Scenario | Condition | Lifetime s | Revocation | Approval subgroup | Intent violations/n | Wilson 95% interval |
| --- | --- | --- | ---: | --- | --- | ---: | --- |
| K1 | S5 | C0 | 900 | none | Approval-dependent | 0/2 | 0.0%–65.8% |
| K1 | S5 | C1 | 900 | none | Approval-dependent | 0/2 | 0.0%–65.8% |
| K1 | S5 | C2 | 900 | none | Approval-dependent | 0/2 | 0.0%–65.8% |

A rubber-stamp approver can permit intent-violating payments within a workflow budget while the workflow counter still prevents the >total chained goal. A null primary H2c/S5 contrast must remain null; supplemental intent effects do not change its definition.

Table III. Descriptive S1 action timing measured in this testbed (authors’ work). Statistics first summarize calls within each run, then describe those run statistics; all timing values are milliseconds.

| Context | Condition | Within-run statistic | Runs | Across-run median ms | Across-run Q1–Q3 ms | Across-run p95 ms |
| --- | --- | --- | ---: | ---: | --- | ---: |
| K1 | C0 | Action latency median | 4 | 48.401 | 45.990–49.575 | 50.634 |
| K1 | C0 | Action latency call p95 | 4 | 52.557 | 48.932–53.568 | 53.632 |
| K1 | C0 | Authorization median | 4 | 0.002 | 0.002–0.002 | 0.002 |
| K1 | C0 | Authorization call p95 | 4 | 0.002 | 0.002–0.002 | 0.002 |
| K1 | C1 | Action latency median | 4 | 45.011 | 42.536–47.755 | 48.405 |
| K1 | C1 | Action latency call p95 | 4 | 50.278 | 47.202–52.549 | 53.896 |
| K1 | C1 | Authorization median | 4 | 0.002 | 0.002–0.002 | 0.002 |
| K1 | C1 | Authorization call p95 | 4 | 0.002 | 0.002–0.002 | 0.002 |
| K1 | C2 | Action latency median | 4 | 47.124 | 46.644–47.825 | 48.677 |
| K1 | C2 | Action latency call p95 | 4 | 50.517 | 49.224–51.894 | 53.726 |
| K1 | C2 | Authorization median | 4 | 2.021 | 1.899–2.137 | 2.238 |
| K1 | C2 | Authorization call p95 | 4 | 2.161 | 1.930–2.398 | 2.468 |

The per-run call p95 values and their call counts are preserved in run-latency-percentiles.csv. Across-run p95 of run medians and across-run p95 of per-run call p95 values are different measurements. No calls are treated as independent experimental replicates; these additional tail summaries are descriptive H4 costs only.
