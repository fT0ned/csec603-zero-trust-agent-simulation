# Completed authorization extension handoff

The separate real-LLM authorization study is complete and independently validated. Read [the measured findings](authorization-findings.md), [paper integration text](authorization-paper-integration.md), [exact measurement meanings](authorization-measurement-notes.md) and [reproduction instructions](authorization-reproduction.md). The precollection tag is `agent-authorization-freeze-v1` at `67f19b5e`; the original `phase2-delivery-v1` release remains unchanged.

## Delivered evidence

- `results/agent-authorization-pilot-001`: initial exploratory attempt, 24 runs, eight interrupted units and retained audit-quality veto. All observations remain preserved.
- `results/agent-authorization-pilot-002`: repaired exploratory feasibility pilot, 24/24 complete, actual unauthorized attempts in all fourteen adversarial cells and authorized completion in all ten positive cells. Separate final prefreeze review retained.
- `results/agent-authorization-study-001`: separately frozen 720/720 full real-LLM units, no failures/reruns, 1,842 provider completions and 1,643 genuine model-generated gateway requests. Independent analysis and additive quality review pass. All 10,800 sealed raw members and 87 captured source files validate.

C0/C1 each committed 150 unauthorized positive mutating effects. C2 denied 163/163 unauthorized requests and committed no unauthorized mutation. Workflow noWF exported twenty distinct records versus C2's ten; RS committed the unrequested payment in 30/30 runs versus careful C2's 0/30. All 300 authorized positive controls completed with no false denials. Extra read attempts during ten positive payment runs are retained, including five gateway-reported successful unauthorized reads in C0/C1; positive completion does not imply an entirely authorized trajectory.

All ten prespecified primary comparisons support new A1–A3 within this fixed synthetic environment. Holm-adjusted p=1.862645149230957e-8; measured risk differences are −1 for eight baseline contrasts and +1 for the two ablations. Wilson upper risk bound for 0/30 remains approximately 11.35%. The observed effects do not establish zero enterprise risk.

## Working environment and cost

The existing Docker/SPIRE/OPA/gateway/private-tool environment is reused. Repairs make vendor/per-action bounds follow trusted delegation, preserve immutable policy/audit snapshots and return recoverable tool errors to the real model. Source, regression tests and the two pilots were committed before freeze. The prefreeze suite passed 142 tests; actual runtime byte/policy/clock checks passed before and after full collection. No provider, source, settings or sample changes occurred during confirmation.

Dashboard: http://127.0.0.1:8765. The current host server was restarted to load the reviewed dashboard projection, PID42520, execution session72420. It observes CLI collections read-only and distinguishes real-LLM/full, real-LLM/pilot and scripted engineering evidence. Use the new study's independent analyzer and protocol; the legacy form does not create or freeze this protocol.

The full study cost estimate was USD0.197885742. The preserved shared ledger totals USD0.768644778 across6,585 settled requests, with no pending reservations, below the unchanged USD4 aggregate cap. No ledger reset, top-up, alternate model or provider fallback occurred. Provider and administrator secrets remain outside Git.

## Reproduce and continue the paper

```powershell
.venv/Scripts/python.exe -m analysis.authorization_study --input results/agent-authorization-study-001 --output .runtime/new-reproduced-analysis
.venv/Scripts/python.exe -m scripts.plot_authorization_study --report .runtime/new-reproduced-analysis/report.json --output .runtime/new-reproduced-figures
```

Use fresh output directories. These commands make no provider calls. The original fourteen analysis/figure outputs reproduced byte-identically before an additional publication layout derivative moved a workflow legend; original figures and their original manifest remain preserved. PDF/SVG/PNG figures, CSV/JSON tables, primary comparisons, full transcripts, independent effects and source seals are committed with the study.

The original real-model null findings, original quality veto, scripted stress and conditional timing results remain separate. H1/H1b retain conditional support; original H2/H3 remain mixed, H2b/H2c unsupported, H3b sanity evidence and H4 descriptive. New A1–A3 support does not retroactively change them. The new study does not measure natural misuse prevalence, jailbreak susceptibility, human approval accuracy, multi-hop delegation or independently delayed JIT expiry.

No further collection is needed for this extension's planned allocation. Remaining IEEE-paper work is integration into the actual existing manuscript, RQ-specific synthesis across evidence classes, exact Appendix A locations, outstanding primary-reference verification, contribution statements and final IEEE PDF inspection/submission. The live Overleaf source and referenced professor email were not supplied. The previously documented GitHub-hosted secret-scanning eligibility issue remains an owner-controlled repository requirement, separate from experimental completion.

## Final export and preservation checks

The current 15,848,602-byte reproducibility ZIP passed 11,770 export checksums, 10,800 raw members, 87 captured sources and ten figure artifacts, with no known local secret found. The first ZIP receipt remains retained: its only captured-source mismatch was a deliberately fake key literal redacted in a test fixture. The exporter now preserves only that exact reviewed source hash when it contains no actual configured secret; regression checks preserve real-secret redaction. Final suite:145 passed. See `docs/verification/authorization-bundle-v2.json`, the retained failed receipt and the included-source reanalysis receipt. Archive path: `.runtime/authorization-reproducibility-v2.zip` (ignored; regenerate through the dashboard).

All31,552 original protected files remain present with unchanged original content; three documentation files have byte-preserving introductory addenda. All original tags and all86 frozen new-study sources remain unchanged.
