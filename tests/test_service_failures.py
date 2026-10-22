"""A committed-but-unacknowledged effect must not release workflow allowance."""
import asyncio
import json
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from testbed import service
from testbed.fixtures import fixture

class FakeHTTP:
    def __init__(self,kind): self.kind=kind
    async def post(self,url,**kwargs):
        request=httpx.Request('POST',url)
        if url==service.OPA:
            if self.kind=='opa_down': raise httpx.ConnectError('unavailable',request=request)
            approval=self.kind=='approval' and kwargs['json']['input'].get('operation')!='receipt'
            return httpx.Response(200,json={'result':{'allow':True,'reason':'allowed','require_approval':approval}},request=request)
        if self.kind=='timeout': raise httpx.ReadTimeout('downstream effect uncertain',request=request)
        if self.kind=='reject': return httpx.Response(422,json={'detail':'rejected before mutation'},request=request)
        return httpx.Response(200,json={'ok':True,'records':5,'amount':0,'result':{}},request=request)

def exercise(tmp_path,kind):
    state={'condition':'C2','credential_id':'test-digest','spiffe_id':'spiffe://test/agent','delegation':fixture('S5',604)['delegation'],
        'workflow':{'records':0,'payment':0},'suspended':False,'revoked':False,'cache':{},'records':[],'audit_count':0,
        'grants':{},'provenance':[],'expected_origin':'agent'}
    with patch.object(service,'ROLE','pa'),patch.object(service,'ADMIN','test-control'),patch.object(service,'HTTP',FakeHTTP(kind)),patch.object(service,'STATE',tmp_path),patch.dict(service.RUNS,{'failure-test':state}),patch.dict(service.LOCKS,{'failure-test':asyncio.Lock()}):
        with TestClient(service.app) as client:
            response=client.post('/control/failure-test/execute',headers={'x-admin-secret':'test-control'},json={
                'run_id':'failure-test','request_id':'write-1','action':'crm.export','params':{'offset':0,'limit':5},'origin':'agent',
                'credential_valid':True,'credential_reason':'valid'})
            assert response.status_code==200
            return state,response.json()

def test_ambiguous_timeout_retains_reservation_and_audit(tmp_path):
    state,result=exercise(tmp_path,'timeout')
    assert state['workflow']['records']==5
    assert result['outcome']=='tool_error' and result['result']['reservation_retained']
    assert result['result']['error']=='ReadTimeout'
    assert state['audit_count']==1

def test_definite_precommit_rejection_releases_reservation(tmp_path):
    state,result=exercise(tmp_path,'reject')
    assert state['workflow']['records']==0
    assert result['outcome']=='tool_error' and not result['result']['effect_uncertain']

def test_policy_transport_failure_is_audited_infrastructure_failure(tmp_path):
    state,result=exercise(tmp_path,'opa_down')
    assert state['workflow']['records']==0
    assert result['outcome']=='infrastructure_error' and not result['allowed']
    assert result['audit']['policy_reason']=='policy_engine_unavailable'

def test_jit_intent_multiplicity_and_duplicate_audit(tmp_path):
    state={'condition':'C2','credential_id':'test-digest','spiffe_id':'spiffe://test/agent','delegation':fixture('S1',604)['delegation'],
        'workflow':{'records':0,'payment':0},'suspended':False,'revoked':False,'cache':{},'records':[],'audit_count':0,
        'grants':{},'provenance':[],'expected_origin':'agent'}
    body={'run_id':'jit-test','request_id':'payment-1','action':'payments.pay',
        'params':{'vendor':'vendor-1','amount':25,'invoice':'invoice-approved'},'origin':'agent','credential_valid':True,'credential_reason':'valid'}
    with patch.object(service,'ROLE','pa'),patch.object(service,'ADMIN','test-control'),patch.object(service,'HTTP',FakeHTTP('approval')),patch.object(service,'STATE',tmp_path),patch.dict(service.RUNS,{'jit-test':state}),patch.dict(service.LOCKS,{'jit-test':asyncio.Lock()}):
        with TestClient(service.app) as client:
            def send():return client.post('/control/jit-test/execute',headers={'x-admin-secret':'test-control'},json=body).json()
            first=send();grant=first['audit']['jit_grant']
            assert first['outcome']=='executed' and grant['used'] and grant['task_id']=='jit-test'
            assert 119<=grant['expires_at']-first['audit']['time']<=120
            duplicate=send()
            assert duplicate['outcome']=='duplicate' and duplicate['approval_count']==0
            assert duplicate['audit']['sequence']==2 and duplicate['audit']['jit_grant'] is None
            body['request_id']='payment-2';repeated=send()
            assert repeated['outcome']=='denied' and 'intent mismatch' in repeated['reason']
            state['revoked']=True;body['request_id']='payment-1';revoked=send()
            assert revoked['outcome']=='denied' and state['audit_count']==4
