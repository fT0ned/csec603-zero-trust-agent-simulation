"""Run inside agent or attacker container; secrets arrive only on stdin."""
import json
import sys
import time
import urllib.request
import urllib.error
import uuid
import math
from .probe import classify_probe, ProbeMeasurementError, VALID

KEYDIR = '/tmp/dpop'

def key_path(run_id): return KEYDIR+'/'+''.join(c for c in run_id if c.isalnum() or c in '-_')+'.pem'

def sign(data):
    # Opt-in (C3): proof signed with the key held only in this container.
    from . import binding
    return binding.make_proof(binding.load_key(key_path(data['data']['run_id'])), data.get('token',''), 'POST', data['url'])

def request(data):
    body = json.dumps(data['data']).encode() if data.get('data') is not None else None
    headers = {'Content-Type':'application/json', 'Authorization':'Bearer '+data.get('token','')}
    if data.get('dpop'): from . import binding  # library import excluded from sign_ms; key load + signing included
    signing = time.perf_counter()
    if data.get('dpop'): headers['DPoP'] = sign(data)
    sign_ms = (time.perf_counter()-signing)*1000
    req = urllib.request.Request(data['url'], data=body, headers=headers)
    start=time.perf_counter()
    try:
        with urllib.request.urlopen(req,timeout=45) as response:
            result=json.load(response);status=response.status
    except urllib.error.HTTPError as error:
        status=error.code;result={'error':error.read().decode()}
    out = {'status':status,'data':result,'latency_ms':(time.perf_counter()-start)*1000,'time':time.time()}
    if data.get('dpop'): out['sign_ms'] = sign_ms
    return out

def keygen(run_id):
    import os
    from . import binding
    os.makedirs(KEYDIR, mode=0o700, exist_ok=True)
    jwk = binding.generate_key(key_path(run_id))
    return {'status':200,'data':{'jwk':jwk,'jkt':binding.thumbprint(jwk)}}

def replay(data):
    """Attacker mode: burst of requests, then periodic probe until first denial or window end. Streams JSON lines."""
    start=time.monotonic(); step=0
    def one(body, kind):
        nonlocal step
        body=dict(body); body['request_id']=uuid.uuid4().hex
        try: result=request({'url':data['url'],'token':data['token'],'data':body})
        except (urllib.error.URLError, OSError, ValueError) as error:
            result={'status':0,'data':{'transport_error_type':type(error).__name__},'latency_ms':None,'time':time.time()}
        step+=1; result.update(kind=kind,step=step,request=body,elapsed_seconds=time.monotonic()-start)
        print(json.dumps(result),flush=True); return result
    for body in data['burst']: one(body,'burst')
    print(json.dumps({'kind':'burst_done','elapsed_seconds':time.monotonic()-start}),flush=True)
    while True:
        r=one(data['probe'],'probe')
        if r['status']!=200 or r['data'].get('allowed') is not True or r['data'].get('outcome')!='executed': break
        if time.monotonic()-start+data['interval']>data['window']: break
        time.sleep(data['interval'])

def main():
    data = json.load(sys.stdin)
    if data.get('mode')=='dpop_keygen': print(json.dumps(keygen(data['run_id'])));return
    if data.get('mode')=='dpop_cleanup':
        import os
        try: os.remove(key_path(data['run_id']))
        except OSError: pass
        print(json.dumps({'status':200,'data':{}}));return
    if data.get('mode')=='replay': replay(data);return
    if not data.get('probe'):
        print(json.dumps(request(data)));return
    timing=data['probe'];start=time.monotonic()
    # first_probe_delay (monotonic, final study) replaces the wall-clock first_probe_at when supplied.
    next_probe=start+(timing['first_probe_delay'] if 'first_probe_delay' in timing else max(0,timing.get('first_probe_at',time.time())-time.time()))
    extended=bool(timing.get('extended'))
    while True:
        wait=next_probe-time.monotonic()
        if wait>0: time.sleep(wait)
        data['data']['request_id']=uuid.uuid4().hex
        try:
            result=request(data)
        except (urllib.error.URLError, OSError, ValueError) as error:
            result={'status':0,'data':{'transport_error_type':type(error).__name__},'latency_ms':None,'time':time.time()}
        result['request']=dict(data['data'])
        result['elapsed_seconds']=time.monotonic()-start
        try: result['probe_classification']=classify_probe(result['status'],result['data'],extended)
        except ProbeMeasurementError as error:
            result['probe_classification']='measurement_failure';result['probe_measurement_error']=error.details
        print(json.dumps(result),flush=True)
        if result['probe_classification']!=VALID or time.time()>=timing.get('deadline',float('inf')) or result['elapsed_seconds']>=timing.get('window',float('inf')): break
        next_probe+=timing['interval']
        if next_probe<time.monotonic(): next_probe+=math.ceil((time.monotonic()-next_probe)/timing['interval'])*timing['interval']

if __name__=='__main__': main()
