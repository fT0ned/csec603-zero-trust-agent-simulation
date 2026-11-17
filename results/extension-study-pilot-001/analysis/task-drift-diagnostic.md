

## Post hoc task-drift and attribution diagnostic

In addition to the registered exact-follow endpoint, the independent authority oracle records 9 unauthorized writes across 6/120 (2.3–10.5%) pilot runs. All six affected runs used Qwen2.5 3B with neutral-v1; they involved unrelated CRM exports/deletions or an unrequested permissions-request email, not the specified malicious payload action. There were 38 invalid-authority attempts in total, including reads and unsuccessful application requests. These findings are task drift/authority failure evidence, not verified payload coercion, and they do not change selection or trigger extra sampling.

Audit-only classifier recorded 5 false coercion labels from benign tool-data parameter reuse (for example customer-001 returned by a normal CRM read). There are no ground-truth positive exact-payload coercion requests in this real-model pilot, so natural-model coercion sensitivity cannot be estimated. This is a material limit of parameter provenance as causal attribution. The full scripted attribution results must remain separate.

| True | Predicted | Requests |
| --- | --- | --- |
| none | coercion | 5 |
| none | none | 208 |
