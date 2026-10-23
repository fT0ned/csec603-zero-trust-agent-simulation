# Fresh final export acceptance

Exports use the exact loopback HTTP `/api/jobs/<batch>/bundle` endpoint as an explicitly documented transport fallback. These archives are not claimed as browser-download artifacts. Each bundle is requested once and checked sequentially after collection/infra idle clearance. No original research files, reviews, configuration or analysis were edited. Browser UI verification is recorded separately by the lead.

| Collection | Archive bytes | Sealed raw members | Captured source files | Figure/table members | Integrity |
|---|---:|---:|---:|---:|---|
| neutral-pilot-001 | 2,522,878 | 420 | 58 | 13 | PASS |
| enforcement-stress-002 | 6,356,026 | 4,590 | 58 | 13 | PASS |
| study-002 | 315,382,821 | 17,333 | 52 | 0 (no figure manifest in this collection) | PASS |

Each completed receipt checks every ZIP file member, SHA-256 coverage, literal original raw seals, captured source hashes, all figure/PDF/table exports and figure-input report hashes, copied quality-assessment hashes, and two known local secret values without revealing them. Before/after guards cover all files in each collection, including raw/source/config/figures. The completed neutral/stress archives have zero changed or added collection files and no secret matches.

The fresh neutral archive was extracted under `.runtime/qa/final-extracted/neutral-pilot-001`. From its included `source/` folder, the repository Python ran:

```powershell
<repo>/.venv/Scripts/python.exe -m analysis.cli --input ../results --output ../reproduced-analysis --verify-raw
```

Exit 0: 36 runs, 420 raw files verified, zero load errors; all 15 reproduced metrics.csv rows equal the exported original rows exactly. Reproduced outputs are beside the extracted copy, not in original research folders.

Archive integrity is independent of scientific quality. Original study-002 retains its failed validation and separately bound endpoint-semantic veto; no ZIP verification upgrades those findings to an accepted study. The final full-study receipt confirms the preserved sealed checkpoint.json.tmp is present and valid, and the bound external semantic adjudication is copied with its recorded hash. Its aggregate scientific quality remains FAILED.

Machine-readable receipts: `final-bundle-neutral-pilot-001.json`, `final-bundle-enforcement-stress-002.json`, and `final-bundle-study-002.json`. Archives are under ignored `.runtime/qa/final-bundles/`.

All three fresh archives passed strict integrity verification. The full archive checked 18,744 file members, 18,742 exported checksums, all 17,333 original raw members and 52 captured source files. Across the three collection guards, no recorded file changed and no collection file was added. The neutral/stress archives each include all 13 figure/table exports, including their three PDFs. No original or repair research, review, configuration or analysis was modified. Dashboard/browser checks are in the lead's separate receipt.
