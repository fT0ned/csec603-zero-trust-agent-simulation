"""Run inside agent or attacker container; secrets arrive only on stdin."""
import json
import sys
import time
import urllib.request
import urllib.error
import uuid

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
    timing=data['probe'];start=time.monotonic();next_probe=start
    while True:
        wait=next_probe-time.monotonic()
        if wait>0: time.sleep(wait)
        data['data']['request_id']=uuid.uuid4().hex
        result=request(data);result['request']=dict(data['data'])
        result['elapsed_seconds']=time.monotonic()-start
        print(json.dumps(result),flush=True)
        if result['status']!=200 or result['data'].get('outcome')!='executed' or time.time()>=timing.get('deadline',float('inf')) or result['elapsed_seconds']>=timing.get('window',float('inf')): break
        next_probe+=timing['interval']
        if next_probe<time.monotonic(): next_probe=time.monotonic()

if __name__=='__main__': main()
