"""Read-only source and clock evidence for the new authorization collector."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
from testbed.common import ROOT, write_json


FILES = {'pa': ['testbed/service.py', 'testbed/common.py'],
         'gateway': ['testbed/service.py', 'testbed/common.py'],
         'agent-client': ['testbed/client.py', 'testbed/probe.py'],
         'crm': ['infra/tools.py'], 'payments': ['infra/tools.py'],
         'email': ['infra/tools.py'], 'files': ['infra/tools.py']}


def verify():
    checks = []
    program = ('import hashlib,json,sys,time; from pathlib import Path; '
               'names=json.load(sys.stdin); '
               'print(json.dumps({"time":time.time(),"files":{n:hashlib.sha256(Path("/app",n).read_bytes()).hexdigest() for n in names}}))')
    for service, names in FILES.items():
        start = time.time()
        result = subprocess.run(['docker', 'compose', 'exec', '-T', service, 'python', '-c', program],
                                input=json.dumps(names), cwd=ROOT, text=True, capture_output=True, timeout=30, check=True)
        end = time.time(); captured = json.loads(result.stdout)
        checks.append({'service': service, 'started_at': start, 'finished_at': end,
                       'container_time': captured['time'], 'clock_within_bracket': start-1 <= captured['time'] <= end+1,
                       'files': {name: {'sha256': sha, 'matches': hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == sha}
                                 for name, sha in captured['files'].items()}})
    # OPA's image has no Python/shell. Read the actual policy through docker cp.
    container = subprocess.check_output(['docker', 'compose', 'ps', '-q', 'opa'], cwd=ROOT, text=True).strip()
    target = ROOT/'.runtime'/'authorization-policy-readback.rego'
    subprocess.run(['docker', 'cp', container+':/policies/policy.rego', str(target)], cwd=ROOT, check=True, capture_output=True)
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    policy_matches = actual == hashlib.sha256((ROOT/'infra/opa/policy.rego').read_bytes()).hexdigest()
    services = subprocess.check_output(['docker', 'compose', 'ps', '--format', 'json'], cwd=ROOT, text=True)
    passed = policy_matches and all(c['clock_within_bracket'] and all(f['matches'] for f in c['files'].values()) for c in checks)
    return {'kind': 'read-only runtime byte and clock verification; no provider calls', 'created_at': time.time(),
            'passed': passed, 'checks': checks, 'opa_policy_sha256': actual, 'opa_policy_matches': policy_matches,
            'compose_state': [json.loads(line) for line in services.splitlines() if line]}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('Use a fresh verification output')
    result = verify(); write_json(args.output, result)
    print(json.dumps({'passed': result['passed'], 'services_checked': len(result['checks'])}))
    return 0 if result['passed'] else 2


if __name__ == '__main__': raise SystemExit(main())
