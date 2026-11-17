"""Study002 health, code, identity boundary and host clock checks, without inference."""
import hashlib
import json
import os
import subprocess
import time

import httpx

from testbed.common import ROOT,write_json
from .harness import compose


def verify(config):
    from .study import verify_models,verify_protected
    verify_models(config);verify_protected()
    if float(os.getenv('STUDY_BUDGET_USD','0'))!=25:raise ValueError('established total budget must remain25')
    services=[json.loads(line) for line in compose('ps','--format','json').splitlines() if line.strip()]
    if len(services)!=19 or any(s.get('Health')!='healthy' for s in services):raise RuntimeError('all nineteen services must be healthy')
    files=[p.relative_to(ROOT).as_posix() for p in (ROOT/'testbed/extension2').glob('*.py')]
    files+=['testbed/common.py','testbed/extension/security.py','testbed/binding.py']
    expected={n:hashlib.sha256((ROOT/n).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for n in files}
    program="import json,pathlib,hashlib;print(json.dumps({n:hashlib.sha256(pathlib.Path(n).read_bytes().replace(b'\\r\\n',b'\\n')).hexdigest() for n in "+repr(files)+"}))"
    matched=[]
    for service in ('extension2-pdp','extension2-pep','extension2-agent-a','extension2-agent-b','extension2-thief'):
        if json.loads(compose('exec','-T',service,'python','-c',program))!=expected:raise RuntimeError('runtime source mismatch: '+service)
        matched.append(service)
    targets=[]
    for name,network in [('extension2-pdp','control'),('files','tools'),('email','tools'),('crm','tools'),('payments','tools')]:
        cid=compose('ps','-q',name).strip()
        info=json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0]
        targets.append((name,info['NetworkSettings']['Networks']['csec603-testbed_'+network]['IPAddress']))
    program='''import socket,json
targets='''+repr(targets)+'''
out=[]
for name,ip in targets:
 try:
  s=socket.create_connection((ip,8000),.3);s.close();reachable=True
 except OSError:reachable=False
 out.append({'target':name,'reachable':reachable})
print(json.dumps(out))'''
    reachability=json.loads(compose('exec','-T','extension2-thief','python','-c',program))
    if any(r['reachable'] for r in reachability):raise RuntimeError('thief can bypass study002 PEP')
    resolved=json.loads(compose('config','--format','json'))
    for name in matched:
        if any('API_KEY' in key or 'STUDY_BUDGET' in key for key in resolved['services'][name].get('environment',{})):
            raise ValueError('provider credential entered study002 container')
    clocks=[]
    with httpx.Client(timeout=5,trust_env=False) as client:
        for port in (8778,8779):
            before=time.time();health=client.get('http://127.0.0.1:'+str(port)+'/health').json();after=time.time()
            low,high=health['time']-after,health['time']-before
            if low < -1 or high >1:raise RuntimeError('clock outside one-second bracket')
            clocks.append({'port':port,'offset_low':low,'offset_high':high})
    return {'passed':True,'checked_at':time.time(),'healthy_services':len(services),'runtime_sources':expected,
            'source_matched_services':matched,'thief_reachability':reachability,'clock_brackets':clocks,
            'topology':'single Windows PC, network-separated Docker services; not multi-host'}


if __name__=='__main__':
    config=json.loads((ROOT/'configs/extension-study-002.json').read_text(encoding='utf-8'))
    result=verify(config);write_json(ROOT/'docs/extension-study-002-preflight.json',result)
    print(json.dumps({'passed':True,'healthy_services':result['healthy_services']}))
