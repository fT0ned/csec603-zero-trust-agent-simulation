# Results measured in this testbed

Preserved input runs: 390. Read errors: 0.

Collection and model context (dates derived from preserved run timestamps):

K1: collection `enforcement-stress-002-dd456530b192`; agent mode `scripted`; phase `engineering`; requested model `always-obey-script`; returned model `always-obey-script`; collection dates 2026-10-23 UTC.

Table I. Run outcomes with Wilson 95% intervals (authors’ work). Context keys preserve collection/model/date; approval subgroups are separate experimental strata.

| Context | Scenario | Condition | Lifetime s | Revocation | Approval subgroup | Outcomes/n | Wilson interval |
| --- | --- | --- | ---: | --- | --- | ---: | --- |
| K1 | S1 | C0 | 900 | none | Not applicable | 0/30 | 0.0%–11.4% |
| K1 | S1 | C1 | 900 | none | Not applicable | 0/30 | 0.0%–11.4% |
| K1 | S1 | C2 | 900 | none | Not applicable | 0/30 | 0.0%–11.4% |
| K1 | S2 | C0 | 900 | none | Other payloads | 15/15 | 79.6%–100.0% |
| K1 | S2 | C1 | 900 | none | Other payloads | 15/15 | 79.6%–100.0% |
| K1 | S2 | C2 | 900 | none | Other payloads | 0/15 | 0.0%–20.4% |
| K1 | S2 | C2-RS | 900 | none | Other payloads | 0/15 | 0.0%–20.4% |
| K1 | S2 | C2-noWF | 900 | none | Other payloads | 0/15 | 0.0%–20.4% |
| K1 | S2 | C0 | 900 | none | Approval-dependent | 15/15 | 79.6%–100.0% |
| K1 | S2 | C1 | 900 | none | Approval-dependent | 15/15 | 79.6%–100.0% |
| K1 | S2 | C2 | 900 | none | Approval-dependent | 0/15 | 0.0%–20.4% |
| K1 | S2 | C2-RS | 900 | none | Approval-dependent | 15/15 | 79.6%–100.0% |
| K1 | S2 | C2-noWF | 900 | none | Approval-dependent | 0/15 | 0.0%–20.4% |
| K1 | S5 | C0 | 900 | none | Other payloads | 15/15 | 79.6%–100.0% |
| K1 | S5 | C1 | 900 | none | Other payloads | 15/15 | 79.6%–100.0% |
| K1 | S5 | C2 | 900 | none | Other payloads | 0/15 | 0.0%–20.4% |
| K1 | S5 | C2-RS | 900 | none | Other payloads | 0/15 | 0.0%–20.4% |
| K1 | S5 | C2-noWF | 900 | none | Other payloads | 15/15 | 79.6%–100.0% |
| K1 | S5 | C0 | 900 | none | Approval-dependent | 15/15 | 79.6%–100.0% |
| K1 | S5 | C1 | 900 | none | Approval-dependent | 15/15 | 79.6%–100.0% |
| K1 | S5 | C2 | 900 | none | Approval-dependent | 0/15 | 0.0%–20.4% |
| K1 | S5 | C2-RS | 900 | none | Approval-dependent | 0/15 | 0.0%–20.4% |
| K1 | S5 | C2-noWF | 900 | none | Approval-dependent | 0/15 | 0.0%–20.4% |

Inference is restricted to this single-machine testbed, these payloads and the recorded model/date. Configuration-guaranteed denials and tamper checks are sanity checks. Scripted runs do not establish real-LLM findings.

Comparisons are in comparisons.csv, including missing contrasts, exact test names, right-minus-left effects, deterministic bootstrap intervals and Holm-adjusted p-values. hypothesis-assessment.json maps each planned contrast to its hypothesis and requires a complete frozen real-LLM study, adjusted significance and the prespecified practical difference. Engineering/pilot comparisons remain descriptive.

Replay times remain censored where validity outlasted observation. No mean or ordinary median is computed for those times. Kaplan–Meier curves use first observed denial and must be interpreted at the recorded probe resolution.

Table II. Supplemental intent violations on approval-dependent S5 payloads (authors’ work). This does not replace the primary chained-total outcome.

| Context | Scenario | Condition | Lifetime s | Revocation | Approval subgroup | Intent violations/n | Wilson 95% interval |
| --- | --- | --- | ---: | --- | --- | ---: | --- |
| K1 | S5 | C0 | 900 | none | Approval-dependent | 15/15 | 79.6%–100.0% |
| K1 | S5 | C1 | 900 | none | Approval-dependent | 15/15 | 79.6%–100.0% |
| K1 | S5 | C2 | 900 | none | Approval-dependent | 0/15 | 0.0%–20.4% |
| K1 | S5 | C2-RS | 900 | none | Approval-dependent | 15/15 | 79.6%–100.0% |
| K1 | S5 | C2-noWF | 900 | none | Approval-dependent | 0/15 | 0.0%–20.4% |

A rubber-stamp approver can permit intent-violating payments within a workflow budget while the workflow counter still prevents the >total chained goal. A null primary H2c/S5 contrast must remain null; supplemental intent effects do not change its definition.

Table III. Descriptive S1 action timing measured in this testbed (authors’ work). Statistics first summarize calls within each run, then describe those run statistics; all timing values are milliseconds.

| Context | Condition | Within-run statistic | Runs | Across-run median ms | Across-run Q1–Q3 ms | Across-run p95 ms |
| --- | --- | --- | ---: | ---: | --- | ---: |
| K1 | C0 | Action latency median | 30 | 47.813 | 43.561–57.709 | 69.264 |
| K1 | C0 | Action latency call p95 | 30 | 50.929 | 46.379–65.457 | 81.675 |
| K1 | C0 | Authorization median | 30 | 0.002 | 0.001–0.002 | 0.003 |
| K1 | C0 | Authorization call p95 | 30 | 0.002 | 0.002–0.002 | 0.005 |
| K1 | C1 | Action latency median | 30 | 56.609 | 46.905–66.567 | 92.249 |
| K1 | C1 | Action latency call p95 | 30 | 64.068 | 48.886–73.884 | 116.227 |
| K1 | C1 | Authorization median | 30 | 0.002 | 0.001–0.002 | 0.002 |
| K1 | C1 | Authorization call p95 | 30 | 0.002 | 0.002–0.002 | 0.003 |
| K1 | C2 | Action latency median | 30 | 52.967 | 46.545–63.157 | 86.379 |
| K1 | C2 | Action latency call p95 | 30 | 59.910 | 50.977–69.993 | 103.944 |
| K1 | C2 | Authorization median | 30 | 1.867 | 1.717–2.091 | 3.043 |
| K1 | C2 | Authorization call p95 | 30 | 2.060 | 1.794–2.428 | 3.997 |

The per-run call p95 values and their call counts are preserved in run-latency-percentiles.csv. Across-run p95 of run medians and across-run p95 of per-run call p95 values are different measurements. No calls are treated as independent experimental replicates; these additional tail summaries are descriptive H4 costs only.
