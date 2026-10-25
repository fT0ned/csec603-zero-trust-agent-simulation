# Latency, authorization overhead and approval load (descriptive, run medians; runs share one host)

| Source | Condition | Runs | Action latency ms | Authorization ms | Approvals/Extra | Approval delay ms |
|---|---|---|---|---|---|---|
| A S1 | C0 | 30 | 149.47 (IQR 126.40-202.60) | 0.00 (IQR 0.00-0.00) | 0.00 | 0.00 |
| A S1 | C1 | 30 | 184.55 (IQR 137.29-334.12) | 0.00 (IQR 0.00-0.00) | 0.00 | 0.00 |
| A S1 | C2 | 30 | 224.51 (IQR 146.96-523.61) | 6.78 (IQR 2.58-26.74) | 1.00 | 0.02 |
| A S1 | C2-AS | 30 | 185.58 (IQR 147.06-420.32) | 4.34 (IQR 2.52-16.32) | 1.00 | 0.02 |
| A S1 | C3 | 30 | 167.35 (IQR 146.41-271.65) | 4.90 (IQR 2.54-23.69) | 1.00 | 0.02 |
| A S1 | C3-AS | 30 | 190.22 (IQR 152.67-250.73) | 4.18 (IQR 2.59-14.37) | 1.00 | 0.01 |
| B positive-export | C0 | 30 | 66.42 (IQR 60.06-72.20) | 0.00 (IQR 0.00-0.00) | false denials 0 | 0.00 (IQR 0.00-0.00) |
| B positive-export | C1 | 30 | 60.17 (IQR 52.48-65.91) | 0.00 (IQR 0.00-0.00) | false denials 0 | 0.00 (IQR 0.00-0.00) |
| B positive-export | C2 | 30 | 64.68 (IQR 51.99-72.02) | 1.97 (IQR 1.69-2.26) | false denials 0 | 0.00 (IQR 0.00-0.00) |
| B positive-export | C2-AS | 30 | 67.26 (IQR 55.30-75.29) | 1.88 (IQR 1.74-2.21) | false denials 0 | 0.00 (IQR 0.00-0.00) |
| B positive-export | C2-RS | 30 | 67.60 (IQR 58.18-74.59) | 1.88 (IQR 1.74-2.20) | false denials 0 | 0.00 (IQR 0.00-0.00) |
| B positive-export | C2-noWF | 30 | 68.60 (IQR 59.28-73.65) | 1.96 (IQR 1.70-2.31) | false denials 0 | 0.00 (IQR 0.00-0.00) |
| B positive-export | C3 | 30 | 61.57 (IQR 56.15-70.62) | 1.88 (IQR 1.70-2.07) | false denials 0 | 0.00 (IQR 0.00-0.00) |
| B positive-payment | C0 | 30 | 57.94 (IQR 45.65-62.18) | 0.00 (IQR 0.00-0.00) | false denials 0 | 0.00 (IQR 0.00-0.00) |
| B positive-payment | C1 | 30 | 56.04 (IQR 45.10-62.69) | 0.00 (IQR 0.00-0.00) | false denials 0 | 0.00 (IQR 0.00-0.00) |
| B positive-payment | C2 | 30 | 61.84 (IQR 50.41-67.23) | 1.93 (IQR 1.74-2.29) | false denials 0 | 0.02 (IQR 0.01-0.02) |
| B positive-payment | C2-AS | 30 | 62.52 (IQR 52.56-70.04) | 1.83 (IQR 1.73-2.09) | false denials 0 | 0.01 (IQR 0.01-0.02) |
| B positive-payment | C2-RS | 30 | 55.45 (IQR 48.86-62.79) | 1.77 (IQR 1.68-1.85) | false denials 0 | 0.01 (IQR 0.01-0.02) |
| B positive-payment | C2-noWF | 30 | 55.69 (IQR 47.60-65.65) | 1.83 (IQR 1.74-2.06) | false denials 0 | 0.01 (IQR 0.01-0.02) |
| B positive-payment | C3 | 30 | 51.31 (IQR 45.16-64.43) | 1.79 (IQR 1.69-1.95) | false denials 0 | 0.01 (IQR 0.01-0.02) |
| C legit | C1 | 30 | 67.47 (IQR 61.71-77.00) | 0.00 (IQR 0.00-0.00) | sign ms n/a |  |
| C legit | C2 | 30 | 64.84 (IQR 52.18-72.30) | 1.94 (IQR 1.81-2.24) | sign ms n/a |  |
| C legit | C2-AS | 30 | 56.68 (IQR 45.55-64.83) | 1.68 (IQR 1.59-1.90) | sign ms n/a |  |
| C legit | C3 | 30 | 66.58 (IQR 56.05-71.32) | 1.96 (IQR 1.80-2.17) | sign ms 8.46 (IQR 7.92-9.35) |  |
| C legit | C3-AS | 30 | 51.31 (IQR 47.17-65.43) | 1.62 (IQR 1.57-1.76) | sign ms 8.08 (IQR 7.61-8.75) |  |
