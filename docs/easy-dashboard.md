# Easy dashboard (`easyboard/`)

A plain-language, read-only results viewer for non-technical readers. It sits beside the older `dashboard/`, which is unchanged.

## Start it

- Windows: double-click `Start-Dashboard.bat` at the repository root. It uses `.venv\Scripts\python.exe` if present, otherwise `py -3`, picks the first free port from 8770 and opens your browser.
- Any platform: `python -m easyboard` (options: `--port N`, `--results DIR`, `--no-browser`). Stop it by closing the window or pressing Ctrl+C.

No packages, build step, npm or internet connection are needed: it is Python standard library plus one HTML file with inline CSS and JavaScript.

## What you see

- **Home**: "What we tested" and one card per study (original study, authorization study, binding study, scripted stress test; the binding pilot appears only if the full binding study is absent) with a one-sentence takeaway, run count and a badge: Real AI model, Scripted test, Pilot or Has quality warning.
- **Study page**: a table comparing protection setups (friendly names, hover for meaning, green/red cells), bar charts of bad outcomes, exposure time and (binding study) the availability cost, a by-situation breakdown, and "What this means / What this does NOT prove".
- **Glossary**: plain-English definitions.

All numbers are computed from `results/<study>/runs/*/summary.json`; only the explanatory sentences are templates. Runs that did not complete, and legitimate-work control runs, are excluded from the counts and the page says how many. The "Has quality warning" badge on the original study comes from the retained timing-quality files under `results/quality-study002/`.

## Safety

The server answers GET only (POST/PUT/DELETE return 405), never opens files for writing, and binds to 127.0.0.1. Tests (`tests/test_easyboard.py`) check that a request sequence leaves a results tree byte- and mtime-identical.

The optional "run the new experiment" page was intentionally not built: launching Docker-driven runs from a browser button is risky for a read-only viewer. Use `python -m scripts.collect_binding_study --config configs/binding-study-pilot.json --output results/<new-folder>` instead.
