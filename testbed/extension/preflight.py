"""Health, source-byte and network-boundary checks without model generation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import httpx

from scripts.spire import compose
from testbed.common import ROOT, write_json
from testbed.extension.study import source_files, verify_local_models


def verify():
    config = json.loads((ROOT / 'configs/extension-study.json').read_text(encoding='utf-8'))
    verify_local_models(config)
    services = [json.loads(line) for line in compose('ps', '--format', 'json').splitlines() if line.strip()]
    if len(services) != 14 or any(s.get('Health') != 'healthy' for s in services):
        raise RuntimeError('every one of fourteen Compose services must be healthy')
    files = [n for n in source_files() if n.startswith('testbed/')]
    original = json.loads((ROOT / 'configs/final-study-freeze.json').read_text(encoding='utf-8'))
    files += [n for n in original['file_hashes'] if n.startswith(('testbed/', 'infra/', 'analysis/', 'scripts/'))]
    files = sorted(set(files))
    program = "import json,hashlib,pathlib;print(json.dumps({n:hashlib.sha256(pathlib.Path(n).read_bytes().replace(b'\\r\\n',b'\\n')).hexdigest() for n in " + repr(files) + "}))"
    host = {n: hashlib.sha256((ROOT / n).read_bytes().replace(b'\r\n', b'\n')).hexdigest() for n in files}
    runtime = {}
    for service in ('extension-pdp', 'extension-pep', 'agent-client', 'extension-agent-b', 'attacker'):
        actual = json.loads(compose('exec', '-T', service, 'python', '-c', program))
        if actual != host:
            raise RuntimeError('runtime source differs: ' + service)
        runtime[service] = actual
    resolved = json.loads(compose('config', '--format', 'json'))
    for service in ('extension-pdp', 'extension-pep', 'extension-agent-b'):
        names = resolved['services'][service].get('environment', {})
        if any('API_KEY' in n or 'STUDY_BUDGET' in n for n in names):
            raise RuntimeError('provider credentials entered container')
    # Use resolved control/tools IPs because internal names should not resolve on front.
    targets = []
    for service in ('extension-pdp', 'files', 'email', 'crm', 'payments'):
        identifier = compose('ps', '-q', service).strip()
        inspected = json.loads(subprocess.check_output(['docker', 'inspect', identifier], text=True))[0]
        net = 'csec603-testbed_control' if service == 'extension-pdp' else 'csec603-testbed_tools'
        targets.append((service, inspected['NetworkSettings']['Networks'][net]['IPAddress'], 8000))
    program = '''import json,socket
targets=''' + repr(targets) + '''
out=[]
for name,ip,port in targets:
 try:
  s=socket.create_connection((ip,port),.4);s.close();reachable=True
 except OSError: reachable=False
 out.append({'service':name,'reachable':reachable})
print(json.dumps(out))'''
    reachability = json.loads(compose('exec', '-T', 'attacker', 'python', '-c', program))
    if any(r['reachable'] for r in reachability):
        raise RuntimeError('attacker can bypass PEP')
    clocks = []
    for port in (8768, 8769):
        before = time.time()
        health = httpx.get(f'http://127.0.0.1:{port}/health', timeout=5).json()
        after = time.time()
        low, high = health['time'] - after, health['time'] - before
        clocks.append({'port': port, 'offset_low': low, 'offset_high': high})
        if low < -1 or high > 1:
            raise RuntimeError('extension clocks outside one-second bracket')
    return {'passed': True, 'checked_at': time.time(), 'services': [{'service': s['Service'], 'health': s['Health']} for s in services],
            'runtime_source_hashes': runtime, 'attacker_reachability': reachability, 'clock_brackets': clocks,
            'trust_boundary': 'single Windows PC, Docker/WSL2; network-separated, not multi-host'}


if __name__ == '__main__':
    result = verify()
    write_json(ROOT / 'docs/extension-preflight.json', result)
    print(json.dumps({'passed': result['passed'], 'healthy_services': len(result['services']), 'source_matched_services': len(result['runtime_source_hashes'])}))
