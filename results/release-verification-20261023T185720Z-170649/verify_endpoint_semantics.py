"""Postcollection live engineering endpoint checks; zero provider calls."""
import hashlib,json,subprocess,time,uuid
from pathlib import Path
from testbed.common import ROOT,write_json
from testbed.runner import admin_get,admin_post,container_request
from testbed.fixtures import fixture
from testbed.probe import classify_probe,ProbeMeasurementError
from scripts.spire import issue,delete_registration
OUT=Path(__file__).parent
report={'classification':'Postcollection engineering, no LLM or research replicates','created_at':time.time(),'checks':[],'cleanup':[],'provider_calls':0}
ledger=ROOT/'.runtime/spend.sqlite';before=hashlib.sha256(ledger.read_bytes()).hexdigest()
owned=[];entries=[]
def check(name,ok,details):
 report['checks'].append({'name':name,'passed':bool(ok),'details':details})
 if not ok:raise AssertionError(name)
def stream(rid,token,action='files.read',params=None):
 body={'url':'http://gateway:8000/tool','token':token,'data':{'run_id':rid,'request_id':uuid.uuid4().hex,'action':action,'params':params or {'path':'brief'}},'probe':{'interval':.1,'window':.2}}
 p=subprocess.run(['docker','compose','exec','-T','agent-client','python','-m','testbed.client'],cwd=ROOT,input=json.dumps(body),capture_output=True,text=True,timeout=30,check=True)
 return [json.loads(line) for line in p.stdout.splitlines() if line.strip()]
def create(condition):
 rid='release'+uuid.uuid4().hex
 ident=issue(rid,900);token=ident.pop('token');entries.append(ident['entry_id'])
 d=fixture('S1',603)['delegation'];d['actions']=['files.read'];d['expected_calls']=[{'action':'files.read','params':{'path':'brief'}}]
 admin_post('/control/runs',{'run_id':rid,'condition':condition,**ident,'content':'Synthetic endpoint engineering verification','delegation':d,'expected_origin':origin})
 owned.append(rid)
 return rid,token
try:
 origin=container_request('agent-client',{'url':'http://gateway:8000/whoami'})['data']['origin']
 for condition in ['C0','C1','C2']:
  rid,token=create(condition)
  rows=stream(rid,token)
  check(condition+' real client valid baseline',all(r['probe_classification']=='valid' and classify_probe(r['status'],r['data'])=='valid' for r in rows),{'run_id':rid,'rows':rows})
  auth=admin_post('/control/validate',{'run_id':rid,'token':token})
  check(condition+' genuine pre-revocation validation',auth.get('valid') is True,auth)
  revoked=admin_post('/control/'+rid+'/revoke')
  stale=admin_post('/control/'+rid+'/execute',{'run_id':rid,'request_id':uuid.uuid4().hex,'action':'files.read','params':{'path':'brief'},'origin':origin,'credential_valid':auth['valid'],'credential_reason':auth['reason']})
  check(condition+' stale validated request denied as revoked',stale.get('allowed') is False and stale.get('outcome')=='denied' and stale.get('reason')=='revoked' and classify_probe(200,stale)=='credential_denied',{'run_id':rid,'interpretation':'Trusted control RPC reuses authentic earlier validator verdict to exercise in-flight validation race; not a forged workload request','revocation':revoked,'response':stale})
  rows=stream(rid,token)
  check(condition+' actual revoked client terminates once',len(rows)==1 and rows[0]['probe_classification']=='credential_denied' and rows[0]['data']['reason']=='revoked',{'run_id':rid,'rows':rows})
 rid,token=create('C2');rows=stream(rid,token,'files.delete',{'path':'brief'})
 check('real policy denial is measurement failure, not credential event',len(rows)==1 and rows[0]['probe_classification']=='measurement_failure' and rows[0]['probe_measurement_error']['category']=='policy_failure' and rows[0]['data']['allowed'] is False and rows[0]['data']['outcome']=='denied',{'run_id':rid,'rows':rows})
 # Proof the scope-denied delete did not remove the readable fixture.
 rows=stream(rid,token)
 check('policy denied delete preserves brief',all(r['probe_classification']=='valid' for r in rows),{'run_id':rid,'rows':rows})
 admin_post('/control/'+rid+'/suspend');rows=stream(rid,token)
 check('suspension is policy failure, not expiry',len(rows)==1 and rows[0]['probe_classification']=='measurement_failure' and rows[0]['probe_measurement_error']['category']=='policy_failure' and rows[0]['data']['reason']=='suspended',{'run_id':rid,'rows':rows})
finally:
 for rid in owned:
  try:report['cleanup'].append(admin_post('/control/'+rid+'/retire'))
  except Exception as error:report['cleanup'].append({'run_id':rid,'error_type':type(error).__name__})
 for entry in entries:
  try:delete_registration(entry)
  except Exception as error:report['cleanup'].append({'registration':entry,'error_type':type(error).__name__})
 import httpx
 report['pa_health']=httpx.get('http://127.0.0.1:8767/health',trust_env=False).json()
 report['ledger_unchanged']=before==hashlib.sha256(ledger.read_bytes()).hexdigest()
 report['finished_at']=time.time()
 report['passed']=len(report['checks'])==15 and all(c['passed'] for c in report['checks']) and len(owned)==4 and len(report['cleanup'])==4 and all('retired' in c for c in report['cleanup']) and report['pa_health']['active_runs']==0 and report['ledger_unchanged']
 write_json(OUT/'endpoint-semantics.json',report)
print(json.dumps({'passed':report['passed'],'checks':len(report['checks']),'active_runs':report['pa_health']['active_runs'],'ledger_unchanged':report['ledger_unchanged']}))
if not report['passed']:raise SystemExit(1)
