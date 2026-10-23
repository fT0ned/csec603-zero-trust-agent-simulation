"""Separate PEP and PA processes. PA serializes policy, JIT and tool effects per task."""
import asyncio
import copy
import json
import os
import time
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
import httpx
import jwt
from fastapi import FastAPI, HTTPException, Request
from .common import canonical, digest, validate_action

ROLE = os.getenv('SERVICE_ROLE', 'gateway')
ADMIN = os.getenv('ADMIN_SECRET', '')
PA = os.getenv('PA_URL', 'http://pa:8000')
OPA = os.getenv('OPA_URL', 'http://opa:8181/v1/data/csec603/decision')
STATE = Path(os.getenv('STATE_DIR', '/state'))
RUNS = {}
LOCKS = {}
DENY_IDS = set()
HTTP = httpx.AsyncClient(timeout=30, trust_env=False)
app = FastAPI(title='Testbed ' + ROLE)

def admin(request):
    if not ADMIN or not secrets.compare_digest(request.headers.get('x-admin-secret', ''), ADMIN):
        raise HTTPException(403, 'Control plane credential required')

def append_record(run_id,state,row):
    row['sequence']=state['audit_count']+1
    row['previous_hash']=state['records'][-1]['hash'] if state['records'] else '0'*64
    row['hash']=digest(row)
    # Nested policy/context objects must remain the values hashed at this event.
    # Later workflow mutations or cached response consumers cannot rewrite them.
    state['records'].append(copy.deepcopy(row));state['records']=state['records'][-32:];state['audit_count']+=1
    STATE.mkdir(parents=True,exist_ok=True)
    with (STATE/(run_id+'.jsonl')).open('a',encoding='utf-8') as stream:
        stream.write(canonical(row)+'\n');stream.flush();os.fsync(stream.fileno())
    return row

async def remote(path, data):
    response = await HTTP.post(PA + path, json=data, headers={'x-admin-secret': ADMIN})
    response.raise_for_status()
    return response.json()

@app.get('/health')
def health():
    return {'status': 'ok', 'role': ROLE, 'active_runs': len(RUNS), 'revoked_credentials':len(DENY_IDS), 'time': time.time()}

@app.get('/whoami')
def whoami(request: Request):
    return {'origin': request.client.host}

@app.post('/control/runs')
async def create_run(request: Request):
    admin(request)
    if ROLE != 'pa': raise HTTPException(404)
    data = await request.json()
    run_id = data['run_id']
    if run_id in RUNS: raise HTTPException(409, 'Run already exists; use a fresh run ID')
    if not run_id.replace('-', '').replace('_', '').isalnum(): raise HTTPException(422, 'Invalid run ID')
    RUNS[run_id] = {**data, 'revoked': False, 'suspended': False, 'workflow': {'records': 0, 'payment': 0},
                    'records': [], 'audit_count':0, 'grants': {}, 'intent_uses':{}, 'cache': {}, 'provenance': []}
    LOCKS[run_id] = asyncio.Lock()
    for tool in ['files', 'email', 'crm', 'payments']:
        url = os.getenv(tool.upper() + '_URL', f'http://{tool}:8000')
        res = await HTTP.post(url + '/reset', json={'run_id': run_id, 'content': data.get('content', '')})
        res.raise_for_status()
    return {'created': run_id}

@app.post('/control/{run_id}/revoke')
async def revoke(run_id: str, request: Request):
    admin(request)
    state = RUNS.get(run_id)
    if state is None: raise HTTPException(404)
    async with LOCKS[run_id]:
        state['revoked'] = True
        state['grants'].clear()
        recorded=time.time()
        response=await HTTP.post(os.getenv('GATEWAY_URL','http://gateway:8000')+'/internal/revoke',
            json={'credential_id':state['credential_id']},headers={'x-admin-secret':ADMIN})
        response.raise_for_status()
        return {**response.json(),'pa_recorded_at':recorded,'credential_id':state['credential_id']}

@app.post('/internal/revoke')
async def gateway_revoke(request:Request):
    admin(request)
    if ROLE!='gateway':raise HTTPException(404)
    data=await request.json();credential_id=data.get('credential_id','')
    if len(credential_id)!=64 or any(ch not in '0123456789abcdef' for ch in credential_id):raise HTTPException(422,'Credential digest required')
    DENY_IDS.add(credential_id)
    return {'active_at':time.time(),'credential_id':credential_id,'enforcement_point':'gateway deny-list'}

@app.post('/control/{run_id}/suspend')
async def suspend(run_id: str, request: Request):
    admin(request)
    if run_id not in RUNS: raise HTTPException(404)
    async with LOCKS[run_id]:
        RUNS[run_id]['suspended'] = True
        RUNS[run_id]['grants'].clear()
    return {'suspended': True}

@app.get('/control/{run_id}/evidence')
async def evidence(run_id: str, request: Request):
    admin(request)
    if run_id not in RUNS: raise HTTPException(404)
    state = RUNS[run_id]
    # Credential bytes never leave the credential validator or appear in evidence.
    return {**{k: state[k] for k in ['records', 'workflow', 'revoked', 'suspended']},'audit_count':state['audit_count'],
            'record_note':'Most recent32 records; full append-only log is retained in PA volume and independently captured by harness.'}

@app.post('/control/{run_id}/retire')
async def retire(run_id: str, request: Request):
    admin(request)
    if ROLE!='pa': raise HTTPException(404)
    if run_id in RUNS:
        async with LOCKS[run_id]:
            RUNS.pop(run_id,None)
        LOCKS.pop(run_id,None)
    return {'retired':run_id,'audit_preserved':True}

@app.post('/control/validate')
async def authenticate(request: Request):
    admin(request)
    data = await request.json(); state = RUNS.get(data.get('run_id'))
    if state is None: return {'valid': False, 'reason': 'unknown task'}
    token = data.get('token', '')
    if digest(token) != state['credential_id']: return {'valid': False, 'reason': 'credential mismatch'}
    if state['revoked']: return {'valid': False, 'reason': 'revoked'}
    if state['condition'] != 'C0':
        try:
            header = jwt.get_unverified_header(token)
            if header.get('alg') not in ['RS256', 'ES256', 'ES384', 'RS384', 'RS512', 'ES512']:
                raise ValueError('Disallowed algorithm')
            jwk = next(k for k in state['jwks']['keys'] if k.get('kid') == header.get('kid'))
            key = jwt.PyJWK.from_dict(jwk).key
            claims = jwt.decode(token, key, algorithms=[header['alg']], audience='csec603-gateway', options={'require':['exp','sub','aud']})
            if claims['sub'] != state['spiffe_id']: raise ValueError('Subject mismatch')
        except Exception:
            return {'valid': False, 'reason': 'invalid or expired JWT-SVID'}
    return {'valid': True, 'reason': 'valid', 'credential_id': state['credential_id']}

@app.post('/tool')
async def tool(request: Request):
    if ROLE != 'gateway': raise HTTPException(404)
    data = await request.json()
    try: validate_action(data.get('action'), data.get('params'))
    except ValueError as e: raise HTTPException(422, str(e))
    token = request.headers.get('authorization', '').removeprefix('Bearer ')
    auth = {'valid':False,'reason':'revoked'} if digest(token) in DENY_IDS else await remote('/control/validate', {'run_id': data.get('run_id'), 'token': token})
    # Origin is the socket peer, never any caller-supplied header/body metadata.
    data['origin'] = request.client.host
    data['credential_valid'] = auth['valid']; data['credential_reason'] = auth['reason']
    return await remote('/control/' + data['run_id'] + '/execute', data)

@app.post('/control/{run_id}/execute')
async def execute(run_id: str, request: Request):
    admin(request)
    if ROLE != 'pa': raise HTTPException(404)
    data = await request.json(); state = RUNS.get(run_id)
    if state is None: raise HTTPException(404)
    try: validate_action(data.get('action'), data.get('params'))
    except ValueError as e: raise HTTPException(422, str(e))
    async with LOCKS[run_id]:
        request_id = data['request_id']; fingerprint = digest({'action':data['action'],'params':data['params']})
        if request_id in state['cache']:
            old_fingerprint, result = state['cache'][request_id]
            if old_fingerprint != fingerprint: raise HTTPException(409, 'Idempotency key reused for different action')
            if data.get('credential_valid') and not state['revoked'] and not state['suspended']:
                receipt_started=time.perf_counter();receipt_allowed=True;receipt_reason='idempotent response; no new effect'
                receipt_input=None;receipt_policy=None;receipt_error=False
                if state['condition'].startswith('C2'):
                    receipt_input={'condition':state['condition'],'action':data['action'],'params':data['params'],
                        'operation':'receipt','delegation':copy.deepcopy(state['delegation']),'workflow':dict(state['workflow']),
                        'identity_valid':True,'suspended':state['suspended']}
                    try:
                        receipt_response=await HTTP.post(OPA,json={'input':receipt_input});receipt_response.raise_for_status()
                        receipt_policy=receipt_response.json().get('result',{})
                        receipt_allowed=bool(receipt_policy.get('allow',False));receipt_reason=receipt_policy.get('reason','fail-closed')
                    except Exception:
                        receipt_allowed=False;receipt_error=True;receipt_reason='policy_engine_unavailable'
                row={k:v for k,v in result['audit'].items() if k not in ['hash','previous_hash','sequence']}
                row.update(time=time.time(),result='duplicate' if receipt_allowed else 'infrastructure_error' if receipt_error else 'denied')
                if state['condition'].startswith('C2'):
                    row.update(origin=data['origin'],policy_decision=receipt_allowed,policy_reason=receipt_reason,
                        policy_input=receipt_input,policy_result=receipt_policy,workflow=dict(state['workflow']),jit_grant=None)
                append_record(run_id,state,row)
                return {**result,'allowed':receipt_allowed,'outcome':row['result'],'reason':receipt_reason,
                    'result':result['result'] if receipt_allowed else None,'duplicate':True,'audit':row,
                    'checkpoint':{'count':state['audit_count'],'hash':row['hash']},'workflow':dict(state['workflow']),
                    'authorization_ms':(time.perf_counter()-receipt_started)*1000,'approval_count':0,'approval_delay_ms':0}
        start = time.perf_counter(); now = time.time()
        allow = data.get('credential_valid', False) and not state['revoked'] and not state['suspended']
        reason = data.get('credential_reason', 'unauthenticated'); approval_count = 0; approval_ms = 0
        # Validation and execution are separate requests. Report the current
        # enforcing state if revocation landed between them; authority is unchanged.
        if state['revoked']: reason = 'revoked'
        elif state['suspended']: reason = 'suspended'
        policy_input = None; policy_result = None; policy_error=False;jit_evidence=None
        if allow and state['condition'].startswith('C2'):
            policy_input = {'condition':state['condition'],'action':data['action'],'params':data['params'],
                            'delegation':copy.deepcopy(state['delegation']),'workflow':dict(state['workflow']),
                            'identity_valid':True,'suspended':state['suspended']}
            try:
                response = await HTTP.post(OPA, json={'input':policy_input}); response.raise_for_status()
                policy_result = response.json().get('result', {})
            except Exception:
                policy_error=True;policy_result={'allow':False,'reason':'policy_engine_unavailable','require_approval':False}
            allow = bool(policy_result.get('allow', False)); reason = policy_result.get('reason', 'fail-closed')
            if allow and policy_result.get('require_approval'):
                approval_start = time.perf_counter(); approval_count = 1
                expected = state['delegation']['expected_calls']
                permitted_uses=sum(x['action']==data['action'] and x['params']==data['params'] for x in expected)
                used_intents=state.setdefault('intent_uses',{})
                careful=used_intents.get(fingerprint,0)<permitted_uses
                approved = state['condition'] == 'C2-RS' or careful
                if approved:
                    grant_id = secrets.token_hex(16)
                    state['grants'][grant_id] = {'fingerprint':fingerprint,'expires':now+120,'used':False,
                        'task':run_id,'credential_id':state['credential_id']}
                    grant = state['grants'][grant_id]
                    allow = (not grant['used'] and time.time()<grant['expires'] and grant['fingerprint']==fingerprint)
                    grant['used'] = True
                    used_intents[fingerprint]=used_intents.get(fingerprint,0)+1
                    jit_evidence={'grant_id':grant_id,'action_hash':fingerprint,'expires_at':grant['expires'],
                        'used':True,'task_id':run_id,'credential_id':state['credential_id']}
                    reason = 'approved one-use JIT' if allow else 'JIT invalid'
                else: allow = False; reason = 'careful approver refused intent mismatch'
                approval_ms = (time.perf_counter()-approval_start)*1000
        auth_ms = (time.perf_counter()-start)*1000
        result = None; outcome = 'infrastructure_error' if policy_error else 'denied'
        if allow:
            tool_name = data['action'].split('.')[0]
            url = os.getenv(tool_name.upper()+'_URL', f'http://{tool_name}:8000')
            reserved_records=data['params'].get('limit',0) if data['action']=='crm.export' else 0
            reserved_payment=data['params'].get('amount',0) if data['action']=='payments.pay' else 0
            # Reserve under the task lock before sending. Unknown downstream outcome retains reservation.
            state['workflow']['records']+=reserved_records
            state['workflow']['payment']+=reserved_payment
            try:
                response = await HTTP.post(url+'/execute', json={k:data[k] for k in ['run_id','request_id','action','params']})
                response.raise_for_status(); result = response.json(); outcome = 'executed' if result.get('ok') else 'tool_error'
                if outcome == 'executed':
                    state['workflow']['records'] += result.get('records', 0)-reserved_records
                    state['workflow']['payment'] += result.get('amount', 0)-reserved_payment
            except Exception as e:
                known_no_effect=isinstance(e,httpx.HTTPStatusError) and 400<=e.response.status_code<500
                if known_no_effect:
                    state['workflow']['records']-=reserved_records;state['workflow']['payment']-=reserved_payment
                outcome = 'tool_error'; result = {'error':type(e).__name__,'effect_uncertain':not known_no_effect,'reservation_retained':not known_no_effect}
        # Provenance is content actually returned by tools, recorded server-side.
        links=[]
        for source in state['provenance']:
            for key,value in data['params'].items():
                if isinstance(value,str) and len(value)>=6 and value in source['text'] and value not in canonical(state['delegation']['expected_calls']):
                    links.append({'parameter':key,'source_request_id':source['request_id'],'value_hash':digest(value)})
                if isinstance(value,(int,float)) and not isinstance(value,bool):
                    import re
                    expected_values=[x['params'].get(key) for x in state['delegation']['expected_calls']]
                    if value not in expected_values and re.search(r'(?<![\w.])'+re.escape(str(value))+r'(?![\w.])',source['text']):
                        links.append({'parameter':key,'source_request_id':source['request_id'],'value_hash':digest(str(value))})
        row={'sequence':state['audit_count']+1,'request_id':request_id,'time':time.time(),
             'credential_id':state['credential_id'],'action':data['action'],'result':outcome}
        if state['condition']!='C0': row['agent']=state['spiffe_id']
        if state['condition'].startswith('C2'):
            row.update({'params':data['params'],'origin':data['origin'],'expected_origin':state.get('expected_origin'),
                'principal':state['delegation']['principal'],'delegation_chain':state['delegation']['chain'],
                'task_id':run_id,'issuance':state.get('issuance',{}),'input_provenance':[x['request_id'] for x in state['provenance']],
                'parameter_provenance':links,'policy_decision':allow,'policy_reason':reason,
                'policy_input':policy_input,'policy_result':policy_result,'workflow':dict(state['workflow']),
                'runtime_signals':{'suspended':state['suspended'],'revoked':state['revoked'],'credential_valid':data.get('credential_valid',False)},
                'jit_grant':jit_evidence})
        append_record(run_id,state,row)
        if outcome=='executed' and data['action'] in ['files.read','email.read','crm.read']:
            content=canonical(result.get('result'))
            content_hash=digest(content)
            if not any(x['content_hash']==content_hash for x in state['provenance']):
                state['provenance'].append({'request_id':request_id,'text':content,'content_hash':content_hash})
                state['provenance']=state['provenance'][-32:]
        output={'allowed':allow,'reason':reason,'outcome':outcome,'result':result,'audit':row,
                'checkpoint':{'count':state['audit_count'],'hash':row['hash']},'authorization_ms':auth_ms,
                'approval_count':approval_count,'approval_delay_ms':approval_ms,'workflow':dict(state['workflow'])}
        state['cache'][request_id]=(fingerprint,output)
        # Read retries have no side effects; retain bounded retry history. All write IDs remain until task retirement.
        if len(state['cache'])>1024:
            for old_id in list(state['cache']):
                if state['cache'][old_id][1]['audit']['action'] in ['files.read','email.read','crm.read','payments.read']:
                    state['cache'].pop(old_id);break
        if len(state['grants'])>128:
            state['grants']={key:value for key,value in state['grants'].items() if not value['used'] and value['expires']>time.time()}
        return output

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app,host='0.0.0.0',port=8000)
