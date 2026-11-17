"""Post-freeze completeness/receipt/primary-unit review; no new samples or tests."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

from testbed.audit import verify as verify_audit
from testbed.common import ROOT, canonical, digest, write_json
from testbed.extension.analyse import read_runs

REQUIRED = {
    'E1-scripted': ('injection_followed', 'unauthorized_outcome', 'legitimate_available'),
    'E1-joint': ('coerced_action_allowed', 'attacker_allowed', 'legitimate_available'),
    'E1-negative': ('unauthorized_outcome',),
    'E2': ('target_allowed',),
    'E3': ('event_allowed', 'response_action', 'legitimate_available', 'recovery_success', 'svid_changed', 'old_token_allowed_after_recovery'),
    'E4-objective': ('unauthorized_outcome', 'task_completed'),
    'E4-replay': ('attacker_allowed', 'legitimate_available', 'task_completed')}


def review(root):
    root = Path(root)
    raw, rows = read_runs(root)
    planned = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    report = json.loads((root / 'analysis/report.json').read_text(encoding='utf-8'))
    by_cell = Counter(r['cell_id'] for r in raw)
    too_many = [k for k, n in by_cell.items() if n > 2]
    mismatches = []
    frozen = json.loads((ROOT / 'configs/extension-study-freeze.json').read_text(encoding='utf-8'))
    for name, expected in frozen['file_hashes'].items():
        if hashlib.sha256((ROOT / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != expected:
            mismatches.append(name)
    missing = []
    invalid_audit = []
    units = {}
    last_suspended = Counter()
    exchange_receipts = 0
    recovery_violations=[]
    positive_chain_grants=Counter()
    for row in rows:
        absent = [name for name in REQUIRED.get(row['experiment'], ()) if row.get(name) is None]
        if absent:
            missing.append({'cell_id': row['cell_id'], 'experiment': row['experiment'], 'fields': absent, 'status': row['status']})
        folder = Path(row['_folder'])
        evidence_file = folder / 'evidence.json'
        if not evidence_file.exists():
            invalid_audit.append({'cell_id': row['cell_id'], 'reason': 'missing evidence'})
        else:
            evidence = json.loads(evidence_file.read_text(encoding='utf-8'))
            verification = verify_audit(evidence['audit'], evidence['checkpoint'])
            if not verification['valid']:
                invalid_audit.append({'cell_id': row['cell_id'], 'reason': verification['reason']})
            exchange_receipts += row.get('verified_exchange_receipts', 0)
            if row['experiment']=='E2' and row['case']=='positive':
                claims=[a['claims'] for a in evidence['audit'] if a.get('kind')=='exchange']
                positive_chain_grants['positive_runs']+=1
                if len(claims)>=2:
                    same=claims[-1]['scope']==claims[-2]['scope'] and claims[-1]['budget']==claims[-2]['budget']
                    positive_chain_grants['equal_A_B_grants' if same else 'different_A_B_grants']+=1
            if row['experiment'] == 'E3':
                last_suspended[(row['strategy'], bool(evidence['suspended']))] += 1
                if row.get('svid_changed') is not True:
                    recovery_violations.append({'cell_id':row['cell_id'],'reason':'SVID bytes not changed'})
                revoked_case=row['strategy']=='suspend-all' or row['event'] in ('bearer-replay','audit-tamper')
                if revoked_case and row.get('old_token_allowed_after_recovery') is not False:
                    recovery_violations.append({'cell_id':row['cell_id'],'reason':'Previously revoked credential allowed'})
        units.setdefault(row['experiment'], Counter())[row['status']] += 1
    planned_ids = {r['cell_id'] for r in planned}
    actual_ids = {r['cell_id'] for r in rows}
    all_terminal = all(r['status'] in ('completed', 'model_step_limit') for r in rows)
    complete = planned_ids == actual_ids and not (missing or invalid_audit or too_many or mismatches) and all_terminal
    # The frozen descriptive primitives omit None values. Apply the protocol's
    # separate completeness requirement before accepting any supported verdict.
    strict = report.get('mechanism_hypotheses', {})
    if not complete:
        strict = {k: {**v, 'verdict': 'inconclusive under strict completeness gate; see missing/failed units'} for k, v in strict.items()}
    result = {'reviewed_at': time.time(), 'complete': complete, 'planned': len(planned), 'primary': len(rows), 'raw': len(raw),
              'primary_status': dict(Counter(r['status'] for r in rows)), 'raw_status': dict(Counter(r['status'] for r in raw)),
              'experiment_status': {k: dict(v) for k, v in units.items()}, 'missing_cells': sorted(planned_ids-actual_ids),
              'unplanned_cells': sorted(actual_ids-planned_ids), 'more_than_one_rerun': too_many,
              'missing_measurements': missing, 'invalid_primary_audits': invalid_audit, 'source_hash_mismatches': mismatches,
              'recovery_invariant_violations':recovery_violations,
              'positive_chain_authority_diagnostic':dict(positive_chain_grants),
              'verified_exchange_receipts': exchange_receipts, 'strict_mechanism_hypotheses': strict,
              'end_of_E3_sequence_suspended': [{'strategy':k[0],'suspended':k[1],'n':n} for k,n in sorted(last_suspended.items())],
              'interpretation': 'E3 first recovery probe precedes an old-token replay. Uniform suspension may therefore re-contain the identity at sequence end; first recovery success is not sustained availability.'}
    write_json(root / 'analysis/quality-review.json', result)
    write_json(root / 'completion-status.json', {k:result[k] for k in ('reviewed_at','complete','planned','primary','raw','primary_status','raw_status')})
    print(json.dumps({k: result[k] for k in ('complete','planned','primary','raw','primary_status','verified_exchange_receipts')}))
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    result = review(parser.parse_args().input)
    raise SystemExit(0 if result['complete'] else 1)
