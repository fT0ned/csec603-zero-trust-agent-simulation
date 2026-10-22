# Zero Trust for Agentic AI

Group Leopard's CSEC 603 Report 2 simulation testbed. Track B evaluates identity, delegation, and accountability controls for an LLM agent operating mock enterprise tools.

Current status: repository initialized for implementation. No testbed, pilot, or experimental results exist in this repository yet.

The controlling project brief is `enterprisePhase2_FINAL.docx`, titled **Leopard Report 2 - Source of Truth**, dated October 21, 2026. Official course requirements and instructor feedback take precedence over the brief. The original documents remain outside this repository in the local parent Phase2 directory; they are not included on GitHub.

We will compare static credentials (C0), attested short-lived identity alone (C1), and full Zero Trust controls (C2). Two C2 variants isolate workflow limits and approval quality. All conditions use the same gateway credential checks and revocation deny-list.

The planned stack is Docker Compose, SPIFFE/SPIRE, Open Policy Agent, a Python gateway and policy administrator, mock files/email/CRM/payments services, a real LLM tool-calling agent, an experiment harness, and reproducible analysis scripts. Versions and provider choices remain to be verified and pinned.

Read [the engineering review](docs/research-brief.md) for the fixed design, build sequence, open parameters, and experiment safeguards.

Keep API keys and disposable credentials outside Git. Only mock enterprise data may be sent to an LLM provider. Do not start full experiments until the pilot and pre-run freeze checklist are complete.
