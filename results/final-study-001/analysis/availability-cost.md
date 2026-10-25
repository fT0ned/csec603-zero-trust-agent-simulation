# Availability cost of auto-suspend and false denials

| Source | Condition | Legitimate agent allowed after attack / false denials |
|---|---|---|
| A S3/300s/none | C2-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| A S3/3600s/none | C2-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| A S3/900s/none | C2-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| A S3/300s/none | C3 | 30/30 (100.0%; 95% CI 88.6-100.0%) |
| A S3/3600s/none | C3 | 30/30 (100.0%; 95% CI 88.6-100.0%) |
| A S3/900s/none | C3 | 30/30 (100.0%; 95% CI 88.6-100.0%) |
| A S3/300s/none | C3-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| A S3/3600s/none | C3-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| A S3/900s/none | C3-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| A S4/300s/expiry | C2-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| A S4/300s/now | C2-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| A S4/3600s/expiry | C2-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| A S4/3600s/now | C2-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| A S4/900s/expiry | C2-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| A S4/900s/now | C2-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| A S4/300s/expiry | C3 | 30/30 (100.0%; 95% CI 88.6-100.0%) |
| A S4/300s/now | C3 | 30/30 (100.0%; 95% CI 88.6-100.0%) |
| A S4/3600s/expiry | C3 | 30/30 (100.0%; 95% CI 88.6-100.0%) |
| A S4/3600s/now | C3 | 30/30 (100.0%; 95% CI 88.6-100.0%) |
| A S4/900s/expiry | C3 | 30/30 (100.0%; 95% CI 88.6-100.0%) |
| A S4/900s/now | C3 | 30/30 (100.0%; 95% CI 88.6-100.0%) |
| A S4/300s/expiry | C3-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| A S4/300s/now | C3-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| A S4/3600s/expiry | C3-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| A S4/3600s/now | C3-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| A S4/900s/expiry | C3-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| A S4/900s/now | C3-AS | 0/30 (0.0%; 95% CI 0.0-11.4%) |
| C | C1 | 30/30 {"valid": 30} |
| C | C2 | 30/30 {"allowed": 30} |
| C | C2-AS | 0/30 {"suspended": 30} |
| C | C3 | 30/30 {"allowed": 30} |
| C | C3-AS | 0/30 {"suspended": 30} |
| B positive-export | C2 | false denials 0 of 60 authorized attempts |
| B positive-export | C2-AS | false denials 0 of 60 authorized attempts |
| B positive-export | C3 | false denials 0 of 60 authorized attempts |
| B positive-payment | C2 | false denials 0 of 89 authorized attempts |
| B positive-payment | C2-AS | false denials 0 of 89 authorized attempts |
| B positive-payment | C3 | false denials 0 of 87 authorized attempts |
