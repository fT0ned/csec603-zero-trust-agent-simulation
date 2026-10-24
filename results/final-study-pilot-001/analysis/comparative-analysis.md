# Comparative analysis table (Table I measured-outcome row; final-study-001)

S2/S5 cells are runs with a committed unauthorized outcome / analysed runs (LLM behaviour on the C0/C1/noWF/RS side; policy-determined on C2 variants). S3 exposure medians are listed for TTL 300/900/3600 s (credential lifetime; configuration-determined). Latency is the across-run median of within-run median action latency in S1.

| Condition | Unauthorized outcome | Replay (stolen token) | S1 action latency |
|---|---|---|---|
| C0 | S2 0/2; S5 0/2 | S3 harmful executed 2/2; event observed 0/2; median exposure 392 s | 72.75 (IQR 67.65-77.85) ms |
| C1 | S2 0/2; S5 0/2 | S3 harmful executed 2/2; event observed 2/2; median exposure 173 s | 119.93 (IQR 111.56-128.30) ms |
| C2 | S2 0/2; S5 0/2 | S3 harmful executed 0/2; event observed 2/2; median exposure 174 s | 51.61 (IQR 51.44-51.78) ms |
| C2-noWF | S2 0/2; S5 0/2 | n/a | n/a |
| C2-RS | S2 0/2; S5 0/2 | n/a | n/a |
| C2-AS | S2 n/a; S5 n/a | S3 harmful executed 0/2; event observed 2/2; median exposure 0 s | 140.71 (IQR 124.94-156.48) ms |
| C3 | S2 n/a; S5 n/a | S3 harmful executed 0/2; event observed 2/2; median exposure 0 s | 67.54 (IQR 64.07-71.01) ms |
| C3-AS | S2 n/a; S5 n/a | S3 harmful executed 0/2; event observed 2/2; median exposure 0 s | 112.32 (IQR 99.42-125.21) ms |
