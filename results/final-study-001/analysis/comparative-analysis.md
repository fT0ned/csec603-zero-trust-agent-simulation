# Comparative analysis table (Table I measured-outcome row; final-study-001)

S2/S5 cells are runs with a committed unauthorized outcome / analysed runs (LLM behaviour on the C0/C1/noWF/RS side; policy-determined on C2 variants). S3 exposure medians are listed for TTL 300/900/3600 s (credential lifetime; configuration-determined). Latency is the across-run median of within-run median action latency in S1.

| Condition | Unauthorized outcome | Replay (stolen token) | S1 action latency |
|---|---|---|---|
| C0 | S2 0/30; S5 0/30 | S3 harmful executed 90/90; event observed 0/90; median exposure 392/992/3692 s | 149.47 (IQR 126.40-202.60) ms |
| C1 | S2 0/30; S5 0/30 | S3 harmful executed 90/90; event observed 90/90; median exposure 172/772/3472 s | 184.55 (IQR 137.29-334.12) ms |
| C2 | S2 0/30; S5 0/30 | S3 harmful executed 0/90; event observed 90/90; median exposure 173/772/3472 s | 224.51 (IQR 146.96-523.61) ms |
| C2-noWF | S2 0/30; S5 0/30 | n/a | n/a |
| C2-RS | S2 0/30; S5 0/30 | n/a | n/a |
| C2-AS | S2 n/a; S5 n/a | S3 harmful executed 0/90; event observed 90/90; median exposure 0/0/0 s | 185.58 (IQR 147.06-420.32) ms |
| C3 | S2 n/a; S5 n/a | S3 harmful executed 0/90; event observed 90/90; median exposure 0/0/0 s | 167.35 (IQR 146.41-271.65) ms |
| C3-AS | S2 n/a; S5 n/a | S3 harmful executed 0/90; event observed 90/90; median exposure 0/0/0 s | 190.22 (IQR 152.67-250.73) ms |
