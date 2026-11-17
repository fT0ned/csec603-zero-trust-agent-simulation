| Scripted event | Policy | Selected actions: counts | Preferred response accuracy, Wilson 95% |
| --- | --- | --- | --- |
| bound-replay | PAA | {"refuse_request": 30} | 30/30 (88.6–100.0%) |
| bound-replay | suspend-all | {"suspend_identity": 30} | 0/30 (0.0–11.4%) |
| bearer-replay | PAA | {"revoke_credential": 30} | 30/30 (88.6–100.0%) |
| bearer-replay | suspend-all | {"suspend_identity": 30} | 0/30 (0.0–11.4%) |
| coercion | PAA | {"deny_keep_identity_flag_input": 30} | 30/30 (88.6–100.0%) |
| coercion | suspend-all | {"suspend_identity": 30} | 0/30 (0.0–11.4%) |
| audit-gap | PAA | {"escalate": 30} | 30/30 (88.6–100.0%) |
| audit-gap | suspend-all | {"suspend_identity": 30} | 0/30 (0.0–11.4%) |
| audit-tamper | PAA | {"contain_identity": 30} | 30/30 (88.6–100.0%) |
| audit-tamper | suspend-all | {"suspend_identity": 30} | 30/30 (88.6–100.0%) |
