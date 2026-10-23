"""Run inside agent or attacker container; secrets arrive only on stdin."""
import json
import sys
import time
import urllib.request
import urllib.error
import uuid
import math
from .probe import classify_probe, ProbeMeasurementError, VALID

def request(data):
    body = json.dumps(data['data']).encode() if data.get('data') is not None else None
    req = urllib.request.Request(data['url'], data=body, headers={
        'Content-Type':'application/json', 'Authorization':'Bearer '+data.get('token','')})
    start=time.perf_counter()
    try:
        with urllib.request.urlopen(req,timeout=45) as response:
            result=json.load(response);status=response.status
    except urllib.error.HTTPError as error:
        status=error.code;result={'error':error.read().decode()}
    return {'status':status,'data':result,'latency_ms':(time.perf_counter()-start)*1000,'time':time.time()}

def main():
    data = json.load(sys.stdin)
    if not data.get('probe'):
        print(json.dumps(request(data)));return
    timing=data['probe'];start=time.monotonic();next_probe=start+max(0,timing.get('first_probe_at',time.time())-time.time())
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
        try: result['probe_classification']=classify_probe(result['status'],result['data'])
        except ProbeMeasurementError as error:
            result['probe_classification']='measurement_failure';result['probe_measurement_error']=error.details
        print(json.dumps(result),flush=True)
        if result['probe_classification']!=VALID or time.time()>=timing.get('deadline',float('inf')) or result['elapsed_seconds']>=timing.get('window',float('inf')): break
        next_probe+=timing['interval']
        if next_probe<time.monotonic(): next_probe+=math.ceil((time.monotonic()-next_probe)/timing['interval'])*timing['interval']

if __name__=='__main__': main()
