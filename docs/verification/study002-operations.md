# Final collection operational record

The final study is `results/study-002` under pushed `study-freeze-v2`. This file records operator observations while collection is incomplete; it makes no final result claims.

At approximately00:53Asia/Dubai on2026-10-23, original attempt `r43814871a91a4597baeba5c80c0fc243` (C2/S4,TTL300,wait-for-expiry,seed624) recorded an infrastructure failure: Windows denied atomic replacement of `checkpoint.json.tmp` with `checkpoint.json` (WinError5/PermissionError). The precise external cause of that access denial was not established. It must not be attributed to antivirus, a policy denial or an attack without evidence.

The failed summary/raw/seal are retained. The frozen collector schedules one same-seed infrastructure rerun after the original1200units; its result remains pending. No frozen code, configuration, model, policy, attack, timing or analysis change was made in response. The original is not converted into a successful attack or a measured unsuccessful attack. Final analysis must report original failures, reruns and any remaining failures explicitly.

## Completion and quality adjudication

The wrapper finished on23October08:21UTC: collection0,analysis0,validation2,balance0. The checkpoint failure received one successful same-cell retry; both original and linked retry remain preserved. See ../study002-quality-review.md for the proven clock correction,31-run scope and quality veto. No original records or frozen analysis were changed.
