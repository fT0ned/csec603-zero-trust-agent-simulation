"""Postcollection cross-checks; never changes the frozen analysis or raw evidence."""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import time
from scipy.stats import binomtest
from testbed.authorization_study import adjudicate
from testbed.audit import tamper_suite
from testbed.common import ROOT, write_json


def review(batch):
    batch = Path(batch); errors = []; files = 0; tamper_checks = 0
    report = json.loads((batch/'analysis/report.json').read_text(encoding='utf-8'))
    assert report['validation_passed'] and report['confirmatory_eligible']
    rows = []; by_condition = defaultdict(Counter); fingerprints = Counter(); models = Counter(); requests = 0
    for folder in sorted((batch/'runs').iterdir()):
        if not folder.is_dir(): continue
        load = lambda name: json.loads((folder/name).read_text(encoding='utf-8'))
        for name, expected in load('raw-manifest.json')['files'].items():
            actual = hashlib.sha256((folder/name).read_bytes()).hexdigest(); files += 1
            if actual != expected: errors.append(folder.name+': changed raw '+name)
        s = load('summary.json'); f = load('fixture.json'); oracle = load('tool-ground-truth.json')
        judged = adjudicate(load('recorded-actions.json'), oracle, f['delegation'])
        if judged['reconciliation_errors']: errors.extend(judged['reconciliation_errors'])
        for key in ('unauthorized_attempts', 'unauthorized_denied', 'unauthorized_allowed', 'unauthorized_committed',
                    'unauthorized_outcome', 'principal_task_completed', 'committed_records', 'committed_payment', 'false_denials'):
            if judged[key] != s[key]: errors.append(folder.name+': reconstruction mismatch '+key)
        s['workflow_limit_exceeded'] = len(oracle['crm']['state']['exports']) > f['delegation']['max_records']
        s['unique_exported_customers'] = len(set(oracle['crm']['state']['exports']))
        rows.append(s)
        for key in ('unauthorized_attempts', 'unauthorized_denied', 'unauthorized_allowed', 'unauthorized_committed', 'false_denials'):
            by_condition[s['condition']][key] += s[key]
        by_condition[s['condition']]['runs'] += 1
        by_condition[s['condition']]['model_tool_failures'] += s.get('model_tool_failures', 0)
        if s['positive_control']:
            by_condition[s['condition']]['positive_runs'] += 1
            by_condition[s['condition']]['positive_required_steps_without_unauthorized_mutation'] += s['principal_task_completed'] and not s['unauthorized_outcome']
            by_condition[s['condition']]['positive_completions_without_any_unauthorized_attempt'] += s['principal_task_completed'] and not s['unauthorized_attempts']
        audits = [json.loads(line) for line in (folder/'audit.jsonl').read_text(encoding='utf-8').splitlines()]
        tests = tamper_suite(audits, load('checkpoint.json')); tamper_checks += len(tests)
        if tests != load('tamper.json') or any(r['valid'] for r in tests.values()): errors.append(folder.name+': tamper-copy check mismatch')
        for t in load('transcript.json'):
            requests += 1; fingerprints[t['response'].get('system_fingerprint')] += 1; models[t['response'].get('model')] += 1
    planned = json.loads((batch/'manifest.json').read_text(encoding='utf-8'))['cells']
    key = lambda r: (r['condition'], r['scenario'], r['seed'], r['pair_id'])
    if Counter(map(key, rows)) != Counter(map(key, planned)): errors.append('independent matrix mismatch')
    independent_tests = []
    for contrast in report['contrasts']:
        groups = [{r['pair_id']: r for r in rows if r['scenario'] == contrast['scenario'] and r['condition'] == c}
                  for c in (contrast['left'], contrast['right'])]
        endpoint = contrast['endpoint']; a, b = groups
        left_only = sum(a[k][endpoint] and not b[k][endpoint] for k in a)
        right_only = sum(b[k][endpoint] and not a[k][endpoint] for k in a)
        n = left_only+right_only
        p = binomtest(min(left_only, right_only), n, .5).pvalue if n else 1.
        effect = sum(int(b[k][endpoint])-int(a[k][endpoint]) for k in a)/len(a)
        if not math.isclose(p, contrast['p_value'], rel_tol=1e-12) or effect != contrast['risk_difference']:
            errors.append('independent SciPy exact-test/effect mismatch')
        independent_tests.append({'scenario': contrast['scenario'], 'left': contrast['left'], 'right': contrast['right'],
                                  'p_value': p, 'risk_difference': effect})
    adjusted = [None]*10; previous = 0.
    for rank, (p, index) in enumerate(sorted((r['p_value'], i) for i, r in enumerate(independent_tests))):
        previous = min(1., max(previous, p*(10-rank))); adjusted[index] = previous
    if adjusted != [c['p_adjusted'] for c in report['contrasts']]: errors.append('independent Holm mismatch')
    with sqlite3.connect('file:'+str(ROOT/'.runtime/spend.sqlite')+'?mode=ro', uri=True) as db:
        ledger = [{'state': state, 'requests': n, 'accounted_usd': amount}
                  for state, n, amount in db.execute('select state,count(*),sum(coalesce(actual,reserved)) from spend group by state')]
    new_cost = 0.; new_requests = 0
    for collection in ('agent-authorization-pilot-001', 'agent-authorization-pilot-002', batch.name):
        for path in (ROOT/'results'/collection).glob('runs/*/transcript.json'):
            for t in json.loads(path.read_text(encoding='utf-8')): new_cost += t.get('cost_usd', 0); new_requests += 1
    settled = next(r for r in ledger if r['state'] == 'settled')
    if len(ledger) != 1 or settled['requests'] != 4633+new_requests or not math.isclose(settled['accounted_usd'], .558286572+new_cost, abs_tol=1e-10):
        errors.append('provider ledger/transcript reconciliation mismatch')
    if settled['accounted_usd'] > 4: errors.append('aggregate budget exceeded')
    freeze = json.loads((batch/'freeze.json').read_text(encoding='utf-8'))
    for name, expected in freeze['file_hashes'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected: errors.append('frozen source changed '+name)
    return {'passed': not errors, 'errors': errors, 'scope': 'Postcollection independent cross-check of frozen findings; no hypothesis or raw changes',
            'created_at': time.time(), 'report_sha256': hashlib.sha256((batch/'analysis/report.json').read_bytes()).hexdigest(),
            'clarification': 'Required-step completion and absence of unauthorized mutation do not rule out extra read attempts. Earlier quality.json clean_positive_completions meant no unauthorized mutation only; its bytes are retained. Use the explicit metrics here and the frozen unauthorized_read_executions endpoint.',
            'reviewer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'observed_units': len(rows),
            'raw_files_rehashed': files, 'tamper_copy_checks': tamper_checks, 'provider_requests_in_full': requests,
            'returned_models': dict(models), 'system_fingerprints': dict(fingerprints), 'condition_totals': dict(by_condition),
            'independent_primary_tests': independent_tests, 'ledger': ledger, 'new_authorization_cost_usd': new_cost,
            'full_study_cost_usd': sum(r['cost_usd'] for r in rows),
            'unique_customer_totals_workflow': {c: sorted(set(r['unique_exported_customers'] for r in rows if r['scenario']=='workflow-export' and r['condition']==c))
                                              for c in ('C0','C1','C2','C2-noWF')},
            'postcollection_host': {'python': sys.version, 'platform': platform.platform(),
                'packages': {name: importlib.metadata.version(name) for name in ('httpx','scipy','matplotlib','fastapi','PyJWT','python-dotenv')}},
            'git_head_at_review': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--input', required=True); p.add_argument('--output', required=True)
    args = p.parse_args(); output = Path(args.output)
    if output.exists(): raise ValueError('Use a fresh review output')
    result = review(args.input); write_json(output, result)
    print(json.dumps({k: result[k] for k in ('passed','errors','observed_units','raw_files_rehashed','tamper_copy_checks','full_study_cost_usd','ledger')}))
    return 0 if result['passed'] else 2


if __name__ == '__main__': raise SystemExit(main())
