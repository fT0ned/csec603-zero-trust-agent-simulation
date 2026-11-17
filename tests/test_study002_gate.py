import asyncio
import copy
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from testbed.extension2 import service
from testbed.extension2.security import Issuer,authority,intent_key,provenance_links
from testbed.extension2.fixtures import fixture
from testbed.extension2.scoring import violations,score
from testbed.extension2.provider import prelude,exposed,application_view,native_messages


@pytest.mark.parametrize('first,second',[(25,25.0),(25.0,25)])
def test_numeric_intent_both_orders_and_independent_oracle(first,second):
    f=fixture('benign',1,0);g=f['delegation'];g['max_payment']=100;g['max_per_payment']=100
    a={'action':'payments.pay','params':{**f['good']['params'],'amount':first}}
    b={'action':'payments.pay','params':{**f['good']['params'],'amount':second}}
    assert authority(a['action'],a['params'],g,{'records':0,'payment':0,'intents':{}})[0]
    used={'records':0,'payment':first,'intents':{intent_key(a):1}}
    assert not authority(b['action'],b['params'],g,used)[0]
    assert 'unrequested_or_consumed_intent' in violations(b,g,[a])
    g['expected_calls'].append(copy.deepcopy(f['good']))
    assert authority(b['action'],b['params'],g,used)[0]


def test_exposure_is_actual_tool_content_and_audit_never_reaches_model():
    f=fixture('bec',1)
    value={'outcome':'executed','result':{'result':{'path':'brief','content':f['content']}},'audit':{'classification':'hidden'},'checkpoint':{'hash':'hidden'}}
    history=prelude(f['task'],'neutral',value)
    assert exposed(history,f['content'])
    assert 'classification' not in json.dumps(history)
    assert native_messages(history)[2]['tool_calls'][0]['function']['arguments']=={'path':'brief'}


def test_truth_partial_follow_and_benign_drift_never_use_prediction():
    f=fixture('bec',3,1);bad=copy.deepcopy(f['bad']);bad['params']['body']='different body'
    request={'request_id':'x',**bad}
    actions=[{'request':request,'source':'model','data':{'outcome':'executed','audit':{'classification':'none'}}}]
    independent={'email':{'write_calls':[{'request_id':'x'}]}}
    result=score(actions,independent,f)
    assert result['coerced_write'] and result['committed_harm'] and not result['exact_follow']
    f['family']='benign';f['malicious_edges']=[]
    result=score(actions,independent,f)
    assert result['drift'] and not result['coerced_write']


def test_numeric_and_string_provenance_do_not_read_attack_truth():
    observed=[{'text':'{"amount":30,"vendor":"attacker-vendor"}','request_id':'r','content_hash':'h'}]
    links=provenance_links({'amount':30.0,'vendor':'attacker-vendor'},observed,[])
    assert {l['parameter'] for l in links}=={'amount','vendor'}
    assert all(not l['already_in_principal_intent'] for l in links)
    nested=[{**observed[0],'text':json.dumps({'content':'Invoice correction: {"amount":30}'})}]
    assert provenance_links({'amount':30.0},nested,[])[0]['parameter']=='amount'


def test_service_semantic_retry_has_one_effect_and_new_request_is_denied(monkeypatch,tmp_path):
    f=fixture('benign',1,0);g=f['delegation'];g['max_payment']=100;g['max_per_payment']=100
    issuer=Issuer();root=issuer.root('r',g['principal'],g['actions'],{'records':2,'payment':100},'A')
    token=issuer.exchange(root,'A',g['actions'],{'records':2,'payment':100},'')
    state={'run_id':'r','condition':'C-PAA-002','delegation':g,'actors':{'A':{'origin':'testclient','spiffe_id':'A'}},
        'audit':[],'provenance':[],'counters':{'records':0,'payment':0,'intents':{}},'suspended':False,'revoked':set(),
        'blocked_svid_digests':set(),'accountability':'complete','cache':{}}
    effects=[]
    class Tool:
        async def post(self,url,**kwargs):
            effects.append(kwargs['json'])
            return httpx.Response(200,request=httpx.Request('POST',url),json={'result':{'paid':True},'amount':25})
    monkeypatch.setattr(service,'ADMIN','unit-admin');monkeypatch.setattr(service,'STATE',tmp_path)
    monkeypatch.setattr(service,'RUNS',{'r':state});monkeypatch.setattr(service,'LOCKS',{'r':asyncio.Lock()})
    monkeypatch.setattr(service,'HTTP',Tool());monkeypatch.setattr(service,'ISSUER',issuer)
    client=TestClient(service.app)
    def send(request_id,amount):
        return client.post('/internal/execute',headers={'x-admin-secret':'unit-admin'},json={'run_id':'r','request_id':request_id,
          'action':'payments.pay','params':{**f['good']['params'],'amount':amount},'_peer':'testclient',
          '_authorization':['Bearer '+token],'_proofs':[],'_url':'http://pep/tool'}).json()
    assert send('one',25)['outcome']=='executed'
    assert send('one',25.0)['outcome']=='duplicate'
    assert send('two',25.0)['outcome']=='denied'
    assert len(effects)==1


@pytest.mark.parametrize('condition,expected_flag',[('C2-002',False),('C-PAA-002',True)])
def test_input_flag_is_persisted_only_by_paa_response(monkeypatch,tmp_path,condition,expected_flag):
    f=fixture('bec',3,1);g=f['delegation'];issuer=Issuer()
    root=issuer.root('r',g['principal'],g['actions'],{'records':2,'payment':25},'A')
    token=issuer.exchange(root,'A',g['actions'],{'records':2,'payment':25},'')
    state={'run_id':'r','condition':condition,'delegation':g,'actors':{'A':{'origin':'testclient','spiffe_id':'A'}},
        'audit':[],'provenance':[{'text':f['content'],'request_id':'source','content_hash':'source-hash'}],
        'counters':{'records':0,'payment':0,'intents':{}},'suspended':False,'revoked':set(),
        'blocked_svid_digests':set(),'accountability':'complete','cache':{}}
    monkeypatch.setattr(service,'ADMIN','unit-admin');monkeypatch.setattr(service,'STATE',tmp_path)
    monkeypatch.setattr(service,'RUNS',{'r':state});monkeypatch.setattr(service,'LOCKS',{'r':asyncio.Lock()});monkeypatch.setattr(service,'ISSUER',issuer)
    response=TestClient(service.app).post('/internal/execute',headers={'x-admin-secret':'unit-admin'},json={'run_id':'r','request_id':'bad',
        **f['bad'],'_peer':'testclient','_authorization':['Bearer '+token],'_proofs':[],'_url':'http://pep/tool'}).json()
    assert not response['allowed'] and response['audit']['classification']=='coercion'
    assert response['audit']['input_flagged']==expected_flag
    assert bool(state['flagged_inputs'])==expected_flag
    assert not state['suspended'] and not state['revoked']


@pytest.mark.parametrize('value',[True,float('nan'),float('inf'),-1])
def test_invalid_amount_rejected(value):
    f=fixture('benign',1)
    with pytest.raises(ValueError):
        authority('payments.pay',{**f['good']['params'],'amount':value},f['delegation'],{'records':0,'payment':0,'intents':{}})
