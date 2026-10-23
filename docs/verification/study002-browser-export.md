# Study-002 original frozen dashboard export QA

This checks the original dashboard release used during study-002, before the separately authorized post-collection UI/export fixes. No experiments, provider calls, testbed resets, source edits, or raw-data changes were performed by this QA. The neutral extension is a separate collection and must not be pooled with this study.

## Browser flow

Edge opened the existing loopback console at http://127.0.0.1:8765, selected study-002, downloaded CSV, JSON, the reproducibility ZIP, and the unauthorized-outcomes SVG. The gzip audit and model transcript for `r1795579b1d6c487db6d7504a10df8620` displayed the real provider request, tools, identity issuance, provenance, policy input/result, and decisions. The comparison view rendered per-run-median latency summaries. Screenshots are stored beside this document.

The UI displayed **REAL LLM / FULL** and **1201 / 1200 finished trials**, with **COMPLETED** collection status. Its validation trace correctly preserves `passed: false`, four credential-handoff schedule errors above one second, and `raw_valid: true`. Collection completion is not a validation pass or permission to treat the timing hypotheses as validated.

## Original-release defects

1. The known sealed member `runs/r43814871a91a4597baeba5c80c0fc243/checkpoint.json.tmp` is rejected by the original trace API with HTTP 404, `File not exportable`. The suffix allowlist uses `Path.suffix`, which is `.tmp`, and the bundle enumerator silently skips rejected files. A completed ZIP can therefore contain its exported raw manifest while omitting that manifest's sealed checkpoint. The machine-readable companion report records the actual missing-member set.
2. The history's finished count includes the retained failed original plus its successful replacement, causing 1201/1200 rather than 1200 completed experimental units plus one retained failed attempt.
3. The dashboard labels collection completion without a prominent warning for failed validation; the user must manually inspect validation.json.
4. A full ZIP request occupies the exporting browser tab while the server first enumerates all allowed files and then sanitizes/recompresses traces. The actual 315,557,817-byte archive took several minutes to prepare; no fabricated small proxy bundle was substituted.

## Suggested minimal separate-release correction

Keep collection state and quality state separate. Read the immutable validation result for an explicit failed-quality warning. Count completed experimental units separately from retained failed attempts. Permit only `runs/<safe run id>/checkpoint.json.tmp` when a bounded JSON object matches the SHA-256 recorded for that exact filename in that run's raw-manifest.json; sanitize it structurally as JSON. Continue rejecting arbitrary temporary files, unsealed files, hash mismatches, and path traversal. Retain the original collected source/config/freeze and label the subsequent dashboard revision as post-collection.

The companion JSON contains checksum, source-byte, gzip, provider-secret and before/after raw-preservation checks for the downloaded original archive. A sanitized export's hashes describe exported bytes and need not equal compressed raw hashes.

## Additional original-release byte-preservation defect

The original exporter parsed/reserialized/recompressed every gzip trace, even when no redaction was required. Comparing exported SHA256SUMS to preserved raw manifests found 7156 sealed exported byte-hash mismatches (7156 gzip traces), in addition to the one omitted checkpoint. Thus passing exported checksums does **not** mean the original bundle can reproduce `analysis.cli --verify-raw`. The separately authorized post-collection exporter scans every bounded JSONL record and copies exact original gzip bytes when clean; altered sealed files receive explicit original/exported-hash provenance and a raw-seal warning. The original downloaded archive remains preserved as QA evidence.
