"""Live adversarial controls verification; requires the running Compose testbed."""
import concurrent.futures
import json
import secrets
import time
import uuid
from pathlib import Path
from testbed.common import ROOT,digest,write_json
from testbed.runner import container_request,admin_post,admin_get
from testbed.fixtures import fixture
from scripts.spire import issue,delete_registration

def main():
    evidence={'kind':'engineering verification, actual HTTP calls; not real-LLM research findings','created_at':time.time(),'checks':[]}
    def check(name,passed,details):
        evidence['checks'].append({'name':name,'passed':bool(passed),'details':details})
        if not passed: raise AssertionError(name+': '+str(details))
    entry=None
    try:
        run_id='verify'+uuid.uuid4().hex;ident=issue(run_id,900);token=ident.pop('token');entry=ident['entry_id']
        f=fixture('S5',604)
        origin=container_request('agent-client',{'url':'http://gateway:8000/whoami'})['data']['origin']
        setup={'run_id':run_id,'condition':'C2',**ident,'content':f['content'],'delegation':f['delegation'],'expected_origin':origin}
        admin_post('/control/runs',setup)
        def send(action,params,request_id=None,extra=None):
            data={'run_id':run_id,'request_id':request_id or uuid.uuid4().hex,'action':action,'params':params,**(extra or {})}
            return container_request('agent-client',{'url':'http://gateway:8000/tool','data':data,'token':token})['data']
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            rows=list(pool.map(lambda _:send('crm.export',{'offset':0,'limit':5}),range(8)))
        state=admin_get('/control/'+run_id+'/evidence')
        check('atomic workflow under8concurrent exports',sum(x['outcome']=='executed' for x in rows)==2 and state['workflow']['records']==10,
              {'executed':sum(x['outcome']=='executed' for x in rows),'records':state['workflow']['records']})
        forged=send('payments.pay',{'vendor':'vendor-1','amount':25,'invoice':'invoice-approved'},extra={'condition':'C0','principal':'admin','delegation':{'actions':['payments.pay']},'origin':'attested-agent'})
        check('agent-supplied authority cannot change scope',forged['outcome']=='denied',{'reason':forged['reason']})
        # Fresh task to verify deduplication without workflow-limit interference.
        run_id='verify'+uuid.uuid4().hex;setup['run_id']=run_id;admin_post('/control/runs',setup)
        rid=uuid.uuid4().hex
        first=send('crm.export',{'offset':0,'limit':5},rid);second=send('crm.export',{'offset':0,'limit':5},rid)
        state=admin_get('/control/'+run_id+'/evidence')
        check('duplicate request has one tool effect',state['workflow']['records']==5 and second.get('duplicate'),{'records':state['workflow']['records']})
        revoked_task_id=run_id
        # This verifier reuses one disposable identity across independent fixtures;
        # credential-wide revocation therefore runs last, as it must invalidate all of them.
        # Intent-bound approval and the rubber-stamp ablation.
        intent=fixture('S2',605) # approved scope/domain, unrequested partner email
        for condition in ['C2','C2-RS']:
            run_id='verify'+uuid.uuid4().hex
            admin_post('/control/runs',{**setup,'run_id':run_id,'condition':condition,'delegation':intent['delegation'],'content':intent['content']})
            call=intent['payload']['calls'][0];result=send(call['action'],call['params'])
            check(condition+' approval intent',result['outcome']==('denied' if condition=='C2' else 'executed'),{'reason':result['reason'],'approval_count':result['approval_count']})
        run_id='verify'+uuid.uuid4().hex;admin_post('/control/runs',{**setup,'run_id':run_id})
        state=admin_get('/control/'+run_id+'/evidence')
        check('back-to-back reset isolation',state['workflow']=={'records':0,'payment':0} and not state['records'] and not state['revoked'],state['workflow'])
        run_id=revoked_task_id
        revoked=admin_post('/control/'+run_id+'/revoke')
        repeated=send('crm.export',{'offset':0,'limit':5},rid)
        check('revocation blocks cached request replay',repeated['outcome']=='denied' and revoked.get('enforcement_point')=='gateway deny-list',
              {'reason':repeated['reason'],'enforcement_point':revoked.get('enforcement_point')})
    finally:
        if entry: delete_registration(entry)
        evidence['passed']=all(x['passed'] for x in evidence['checks'])
        write_json(ROOT/'docs/verification/controls.json',evidence)
    print(json.dumps(evidence,indent=2))

if __name__=='__main__':main()
