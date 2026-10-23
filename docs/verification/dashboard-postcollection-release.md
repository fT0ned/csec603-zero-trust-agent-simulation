# Post-collection dashboard release verification

Verified 2026-10-23, after the original study and enforcement stress collections. Current loopback dashboard: http://127.0.0.1:8765, Python PID 14468, session 25546. Twelve isolated dashboard tests pass. No Docker restart or paid provider call was made by this QA.

## Browser and backend checks

- The staged timing-repair protocol is **prepared**, inactive, with no completed trials. The dashboard never rewrites its protocol/manifest.
- Original study-002 displays **1200 completed units / 1200**, plus **1 retained failed attempt**, and an explicit **Quality validation FAILED** warning preserving the four original schedule errors.
- The sealed failed-run `checkpoint.json.tmp` opens with HTTP 200 and shows the preserved count/hash; arbitrary, unsealed and changed temporary files remain rejected by tests.
- Neutral preset loads `neutral-v1`, `enforcement-extension-v1`, and `exploratory-neutral-pilot`; the selected completed batch shows those values. Stress preset loads scripted mode and its deterministic stress study kind. Stress results show 390 completed units, both CSV/JSON exports have 390 records, and its gzip audit trace returns HTTP 200.
- One explicitly authorized real managed engineering trial was started through the browser: `20261023T132827-875518aa`, C2/S1, scripted, one repeat, one worker, with protocol/study kind `postrelease-engineering`. Browser progress showed running then completed; analysis appeared and the console reset succeeded. All 12 run evidence files remained byte-identical across reset. This control check is not a real-LLM research finding.

## Extracted neutral bundle reproduction

The browser export click reached HTTP 200, but the browser download-event API did not expose a local artifact. The identical loopback endpoint response was saved directly to `.runtime/qa/neutral-pilot-001-release.zip`. This transport limitation is reported rather than claiming an unobserved browser download artifact.

The 2,153,868-byte archive contains 684 valid exported SHA-256 entries. All 108 gzip traces decoded and passed the provider-secret scan. No sealed member was missing or altered; `EXPORT_PROVENANCE.json` records that state. Extraction is under `.runtime/qa/neutral-bundle-release`.

Using the source shipped inside the bundle, from its `source/` directory:

```powershell
<repository>/.venv/Scripts/python.exe -m analysis.cli --input ../results --output ../reproduced-from-bundle-source --verify-raw
```

The command exits 0: 36 runs, all 420 sealed raw files valid, no load errors. All 15 reproduced `metrics.csv` rows equal the exported original rows exactly. The same verification/analysis also passed using the local installed analysis entrypoint. Original sealed/source files in the repository remained unchanged; 5,674 neutral/stress files were guarded before and after QA.

The original study-002 ZIP is intentionally preserved as the earlier defective-export evidence. A new full study ZIP remains deferred until the timing-repair collection has finished to avoid introducing unnecessary host load. This small actual bundle and the targeted sealed-temp/gzip tests verify the corrected exporter independently of the old archive.

Machine-readable evidence is in `dashboard-postcollection-release.json`; screenshots include `dashboard-release-checkpoint.jpg`, engineering progress/completion, and `dashboard-postcollection-release.jpg`. The browser is left on the completed neutral pilot, with no active study selected for repeated evidence reloads.
