"""Binding-study metric extraction, manifest determinism and the offline analyzer (no Docker)."""
import json
from analysis import binding_study as an
from testbed import binding_study as bs
from testbed.common import digest

def row(kind, action, allowed, reason, t, rid):
    outcome = 'executed' if allowed else 'denied'
    return {'kind': kind, 'status': 200, 'elapsed_seconds': t, 'request': {'request_id': rid, 'action': action, 'params': {}},
            'data': {'allowed': allowed, 'outcome': outcome, 'reason': reason}}

def chain(n, **extra):
    rows, prev = [], '0' * 64
    for i in range(1, n + 1):
        r = {'sequence': i, 'previous_hash': prev, 'result': 'x', **extra}; r['hash'] = digest({k: v for k, v in r.items()}); rows.append(r); prev = r['hash']
    return rows, {'count': n, 'hash': prev}

def legit(label, ok):
    return {'label': label, 'status': 200, 'data': {'allowed': ok, 'outcome': 'executed' if ok else 'denied', 'reason': 'allowed' if ok else 'suspended'}, 'latency_ms': 50.0}

def test_metrics_replay_succeeds_until_expiry():
    attacker = [row('burst', 'crm.export', True, 'allowed', .1, 'a'), row('burst', 'email.send', False, 'scope_denied', .2, 'b'),
                row('probe', 'files.read', True, 'allowed', .3, 'c'), row('probe', 'files.read', True, 'allowed', 5.3, 'd'),
                row('probe', 'files.read', False, 'invalid or expired JWT-SVID', 10.3, 'e')]
    ind = {'crm': {'write_calls': [{'request_id': 'a', 'action': 'crm.export', 'response': {'records': 5}}]}, 'email': {'write_calls': []}}
    audits, cp = chain(3, origin='o', expected_origin='e')
    m = bs.run_metrics('C2', [legit('task0', True), legit('task1', True), legit('after_attack', True)], attacker, ind, audits, cp, 300)
    assert m['replay_attempts_allowed'] == 3 and m['first_attacker_success'] and m['burst_export_allowed'] and not m['burst_email_allowed']
    assert m['event_observed'] and m['first_denial_seconds'] == 10.3 and m['exposure_seconds'] == 5.3
    assert m['attacker_committed_records'] == 5 and m['legit_task_completed'] and m['legit_after_attack_allowed'] and m['audit_valid']
    assert m['audit_flags_impersonation'] is True

def test_metrics_blocked_and_censored():
    attacker = [row('burst', 'crm.export', False, 'binding_proof_missing', .1, 'a'), row('probe', 'files.read', False, 'binding_proof_missing', .2, 'c')]
    audits, cp = chain(2)
    m = bs.run_metrics('C3', [legit('task0', True), legit('task1', True), legit('after_attack', True)], attacker, {'crm': {'write_calls': []}}, audits, cp, 300)
    assert not m['first_attacker_success'] and m['exposure_seconds'] == 0.0 and m['first_denial_reason'] == 'binding_proof_missing'
    attacker = [row('probe', 'files.read', True, 'allowed', 0.1, 'a'), row('probe', 'files.read', True, 'allowed', 299.9, 'b')]
    m = bs.run_metrics('C1', [], attacker, {'crm': {'write_calls': []}}, audits, cp, 300)
    assert not m['event_observed'] and m['censored_at_seconds'] == 299.9 and m['audit_c2_fields_complete'] is None

def test_availability_cost_recorded():
    attacker = [row('burst', 'crm.export', False, 'origin_mismatch', .1, 'a')]
    audits, cp = chain(1, response_action='suspend_and_revoke', detection_to_containment_ms=3.0)
    m = bs.run_metrics('C2-AS', [legit('task0', True), legit('task1', True), legit('after_attack', False)], attacker, {}, audits, cp, 300)
    assert not m['legit_after_attack_allowed'] and m['legit_after_attack_reason'] == 'suspended' and m['detection_to_containment_ms'] == 3.0

def test_manifest_is_deterministic_and_balanced():
    cfg = {'repeats': 3, 'seed': 4603}
    assert bs.manifest(cfg) == bs.manifest(cfg) and len(bs.manifest(cfg)) == 15
    assert {c: sum(x['condition'] == c for x in bs.manifest(cfg)) for c in bs.CONDITIONS} == {c: 3 for c in bs.CONDITIONS}

def test_wilson_and_km_censoring():
    lo, hi = an.wilson(30, 30)
    assert hi == 1.0 and 0.88 < lo < 0.89
    km = an.kaplan_meier([(10, True), (20, False), (20, False)])
    assert an.km_quantile(km, .5, 20).startswith('> 20') and an.km_quantile(an.kaplan_meier([(5, True), (6, True)]), .5, 6) == 5

def test_analyzer_end_to_end_is_deterministic(tmp_path):
    root = tmp_path / 'c'; (root / 'runs').mkdir(parents=True); cells = []
    for i, cond in enumerate(('C1', 'C3')):
        c1 = cond == 'C1'
        cells.append({'cell_id': cond + '-00', 'condition': cond, 'replicate': 0})
        r = {'cell_id': cond + '-00', 'condition': cond, 'run_id': 'r%d' % i, 'status': 'completed', 'window_seconds': 300,
             'first_attacker_success': c1, 'burst_export_allowed': c1, 'burst_email_allowed': c1, 'attacker_committed_writes': 2 * c1,
             'attacker_committed_records': 5 * c1, 'replay_attempts_allowed': 40 * c1, 'event_observed': True,
             'first_denial_seconds': 270.2 if c1 else .1, 'censored_at_seconds': None, 'exposure_seconds': 265.0 if c1 else 0.0,
             'first_denial_reason': 'x', 'first_burst_reason': 'y', 'detection_to_containment_ms': None, 'legit_task_completed': True,
             'legit_after_attack_allowed': True, 'legit_after_attack_reason': 'allowed', 'audit_valid': True, 'audit_count': 3,
             'audit_c2_fields_complete': None if c1 else 3, 'audit_flags_impersonation': None if c1 else True, 'tamper_cases': 5, 'tamper_detected': 5,
             'legit_latency_ms_median': 50.0, 'legit_sign_ms_median': None, 'legit_authorization_ms_median': 3.0}
        (root / 'runs' / r['run_id']).mkdir(); (root / 'runs' / r['run_id'] / 'summary.json').write_text(json.dumps(r))
    (root / 'manifest.json').write_text(json.dumps({'cells': cells, 'count': 2, 'phase': 'pilot', 'git_commit': 'a' * 40}))
    an.write_outputs(an.analyse(root), tmp_path / 'o1'); an.write_outputs(an.analyse(root), tmp_path / 'o2')
    for name in ('results.md', 'results.json', 'summary-table.csv', 'survival-km.csv', 'fig-exposure-survival.svg'):
        assert (tmp_path / 'o1' / name).read_bytes() == (tmp_path / 'o2' / name).read_bytes()
    assert 'Mechanism verification' in (tmp_path / 'o1' / 'results.md').read_text(encoding='utf-8')
    assert json.loads((tmp_path / 'o1' / 'results.json').read_text())['conditions']['C1']['attacker_any_request_executed']['text'] == '1/1'
