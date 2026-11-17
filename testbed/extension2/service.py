"""Network-separated extension PEP and PDP/STS/PA, with private synthetic applications.

Only the PEP sees untrusted client requests. PDP control endpoints require the
bootstrap secret and are unreachable from the front network. Issuer state is
ephemeral per collection; public evidence contains claims/digests, never tokens.
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
from pathlib import Path
import secrets
import time

import httpx
import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from testbed.common import canonical, digest, validate_action
from testbed.extension2.security import Issuer, ProofVerifier, actor_path, authority, classify, response_for, intent_key, provenance_links

ROLE = os.getenv('EXTENSION_ROLE', 'pdp')
ADMIN = os.getenv('ADMIN_SECRET', '')
PDP = os.getenv('EXTENSION_PDP', 'http://extension2-pdp:8000')
STATE = Path(os.getenv('EXTENSION_STATE', '.runtime/extension2-service'))
RUNS = {}
LOCKS = {}
ISSUER = Issuer()
PROOFS = ProofVerifier()
app = FastAPI(title='Extension ' + ROLE)
HTTP = httpx.AsyncClient(timeout=20, trust_env=False)
TOOLS = {name: 'http://' + name + ':8000' for name in ('files', 'email', 'crm', 'payments')}


def admin(request):
    if not ADMIN or not secrets.compare_digest(request.headers.get('x-admin-secret', ''), ADMIN):
        raise HTTPException(403, 'control credential required')


async def forward(path, body):
    try:
        result = await HTTP.post(PDP + path, json=body, headers={'x-admin-secret': ADMIN})
        result.raise_for_status()
        return result.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, 'policy_service_unavailable')


def append(state, row):
    row = copy.deepcopy(row)
    row.update(sequence=len(state['audit']) + 1, previous_hash=state['audit'][-1]['hash'] if state['audit'] else '0' * 64)
    row['hash'] = digest(row)
    state['audit'].append(row)
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / (state['run_id'] + '.jsonl')).open('a', encoding='utf-8') as stream:
        stream.write(canonical(row) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    return row


@app.get('/health')
def health():
    return {'ok': True, 'role': ROLE, 'time': time.time(), 'runs': len(RUNS)}


@app.get('/whoami')
def whoami(request: Request):
    return {'origin': request.client.host}


@app.post('/nonce')
async def nonce(request: Request):
    data = await request.json()
    if ROLE == 'pep':
        return await forward('/internal/nonce', data)
    admin(request)
    return {'nonce': PROOFS.nonce(data['context'])}


@app.post('/internal/nonce')
async def internal_nonce(request: Request):
    admin(request)
    data = await request.json()
    return {'nonce': PROOFS.nonce(data['context'])}


@app.post('/admin/start')
async def start(request: Request):
    admin(request)
    if ROLE != 'pdp':
        raise HTTPException(404)
    data = await request.json()
    run_id = data['run_id']
    if not run_id.replace('-', '').replace('_', '').isalnum() or run_id in RUNS:
        raise HTTPException(409, 'fresh safe run id required')
    if data['condition'] not in ('C0-002', 'C1-002', 'C2-002', 'C3-9449-002', 'C-PAA-002', 'C-PAA-B-002'):
        raise HTTPException(422, 'unknown condition')
    state = copy.deepcopy(data)
    state.update(audit=[], provenance=[], counters={'records': 0, 'payment': 0, 'intents': {}}, suspended=False,
                 revoked=set(), blocked_svid_digests=set(), static=secrets.token_urlsafe(32), accountability='complete', cache={})
    RUNS[run_id] = state
    LOCKS[run_id] = asyncio.Lock()
    for name, url in TOOLS.items():
        response = await HTTP.post(url + '/reset', json={'run_id': run_id, 'content': data.get('content', '')})
        response.raise_for_status()
    budget = {'records': data['delegation']['max_records'], 'payment': data['delegation']['max_payment']}
    root = ISSUER.root(run_id, data['delegation']['principal'], data['delegation']['actions'], budget, data['actors']['A']['spiffe_id'])
    state['root_digest'] = digest(root)
    return {'root_token': root, 'static_token': state['static'], 'issuer_jwk': __import__('testbed.extension2.security', fromlist=['public_jwk']).public_jwk(ISSUER.key)}


@app.post('/exchange')
async def exchange(request: Request):
    data = await request.json()
    if ROLE == 'pep':
        data['_peer'] = request.client.host
        data['_proofs'] = request.headers.getlist('dpop')
        data['_url'] = str(request.url)
        return await forward('/internal/exchange', data)
    raise HTTPException(404)


@app.post('/internal/exchange')
async def internal_exchange(request: Request):
    admin(request)
    data = await request.json()
    state = RUNS[data['run_id']]
    started = time.perf_counter()
    try:
        header = jwt.get_unverified_header(data['actor_token'])
        if header['alg'] not in ('ES256', 'ES384', 'RS256', 'RS384', 'RS512', 'ES512'):
            raise ValueError('SVID algorithm')
        # Trust-domain bundle comes only from administrator, not from the client.
        keys = state['svid_jwks']['keys']
        jwk = next(k for k in keys if k.get('kid') == header.get('kid'))
        svid = jwt.decode(data['actor_token'], jwt.PyJWK.from_dict(jwk).key, algorithms=[header['alg']], audience='csec603-gateway',
                          options={'require': ['sub', 'exp', 'aud']})
        actor = next(a for a in state['actors'].values() if a['spiffe_id'] == svid['sub'])
        if data['_peer'] != actor['origin']:
            raise ValueError('actor peer mismatch')
        jkt = None
        if state['condition'] in ('C3-9449-002', 'C-PAA-B-002'):
            if len(data['_proofs']) != 1:
                raise ValueError('one DPoP header required')
            ok, why, jkt = PROOFS.check(data['_proofs'][0], 'POST', data['_url'], 'exchange:' + state['run_id'])
            if not ok:
                raise ValueError(why)
        token = ISSUER.exchange(data['subject_token'], svid['sub'], data['scope'], data['budget'], data.get('next_actor', ''),
                                jkt=jkt, enforce=state['condition'] not in ('C0-002', 'C1-002'), actor_svid_digest=digest(data['actor_token']))
        claims = ISSUER.verify(token, enforce_chain=state['condition'] not in ('C0-002', 'C1-002'))
        receipt = jwt.encode({'iss': 'csec603-study002-audit', 'aud': 'csec603-study002-audit-review', 'iat': int(time.time()),
                              'claims': claims, 'token_digest': digest(token)}, ISSUER.key, algorithm='ES256',
                             headers={'typ': 'csec603-audit+jwt'})
        append(state, {'kind': 'exchange', 'time': time.time(), 'actor': svid['sub'], 'claims': claims,
                       'parent_digest': claims['parent'], 'token_digest': digest(token), 'origin': data['_peer'], 'signed_receipt': receipt})
        return {'ok': True, 'access_token': token, 'token_type': 'DPoP' if jkt else 'Bearer', 'claims': claims,
                'exchange_ms': (time.perf_counter() - started) * 1000}
    except (jwt.PyJWTError, ValueError, TypeError, KeyError, StopIteration):
        append(state, {'kind': 'exchange_denial', 'time': time.time(), 'origin': data.get('_peer'), 'reason': 'invalid_exchange'})
        return {'ok': False, 'reason': 'invalid_exchange', 'exchange_ms': (time.perf_counter() - started) * 1000}


@app.post('/tool')
async def tool(request: Request):
    if ROLE != 'pep':
        raise HTTPException(404)
    data = await request.json()
    try:
        validate_action(data['action'], data['params'])
    except (ValueError, KeyError):
        raise HTTPException(422, 'invalid action schema')
    data['_peer'] = request.client.host
    data['_authorization'] = request.headers.getlist('authorization')
    data['_proofs'] = request.headers.getlist('dpop')
    data['_url'] = str(request.url)
    result = await forward('/internal/execute', data)
    if result.get('dpop_required') and not result['audit']['possession_valid']:
        challenge = await forward('/internal/nonce', {'context': 'resource:' + data['run_id']})
        return JSONResponse(result, status_code=401, headers={
            'DPoP-Nonce': challenge['nonce'], 'WWW-Authenticate': 'DPoP error="invalid_dpop_proof"'})
    return result


@app.post('/internal/execute')
async def execute(request: Request):
    admin(request)
    data = await request.json()
    state = RUNS[data['run_id']]
    async with LOCKS[state['run_id']]:
        started = time.perf_counter()
        validate_action(data['action'], data['params'])
        request_id = data['request_id']
        fingerprint = digest(intent_key({'action': data['action'], 'params': data['params']}))
        token = ''
        identity_valid = False
        possession_valid = False
        claims = {}
        expected = None
        reason = 'invalid_identity'
        try:
            if len(data['_authorization']) != 1:
                raise ValueError('one authorization header required')
            scheme, token = data['_authorization'][0].split(' ', 1)
            if state['condition'] == 'C0-002':
                identity_valid = secrets.compare_digest(token, state['static']) and scheme == 'Bearer'
                if identity_valid:
                    expected = state['actors']['A']['origin']
            else:
                claims = ISSUER.verify(token, enforce_chain=state['condition'] != 'C1-002')
                if claims['task'] != state['run_id']:
                    raise ValueError('task mismatch')
                identity_valid = True
                current = claims['act']['sub']
                expected = next(a['origin'] for a in state['actors'].values() if a['spiffe_id'] == current)
            if digest(token) in state['revoked']:
                identity_valid = False
            possession_valid = identity_valid
            if state['condition'] in ('C3-9449-002', 'C-PAA-B-002'):
                if scheme != 'DPoP' or len(data['_proofs']) != 1:
                    possession_valid = False
                    reason = 'invalid_dpop_scheme_or_header'
                else:
                    possession_valid, reason, _ = PROOFS.check(data['_proofs'][0], 'POST', data['_url'], 'resource:' + state['run_id'],
                                                              binding=claims.get('cnf', {}).get('jkt', ''), token=token)
            elif scheme != 'Bearer':
                possession_valid = False
            if not identity_valid:
                reason = 'revoked_or_invalid_identity'
        except (ValueError, TypeError, KeyError, jwt.PyJWTError, StopIteration):
            identity_valid = possession_valid = False
        allowed_authority, authority_reason = authority(data['action'], data['params'], state['delegation'], state['counters'])
        if claims and state['condition'] in ('C2-002', 'C3-9449-002', 'C-PAA-002', 'C-PAA-B-002'):
            if data['action'] not in claims['scope']:
                allowed_authority, authority_reason = False, 'capability_scope'
            if data['action'] == 'crm.export' and state['counters']['records'] + data['params']['limit'] > claims['budget']['records']:
                allowed_authority, authority_reason = False, 'capability_budget'
            if data['action'] == 'payments.pay' and state['counters']['payment'] + data['params']['amount'] > claims['budget']['payment']:
                allowed_authority, authority_reason = False, 'capability_budget'
        cached = state['cache'].get(request_id)
        if cached and cached['fingerprint'] != fingerprint:
            raise HTTPException(409, 'idempotency conflict')
        if (cached and possession_valid and not state['suspended'] and digest(token) not in state['revoked']
                and cached.get('token_digest') == digest(token)):
            allowed_authority, authority_reason = True, 'idempotent_replay'
        links = provenance_links(data['params'], state['provenance'], state['delegation']['expected_calls'])
        row = {'kind': 'action', 'time': time.time(), 'request_id': request_id, 'origin': data['_peer'], 'expected_origin': expected,
               'identity_valid': identity_valid, 'possession_valid': possession_valid, 'authority_valid': allowed_authority,
               'authority_reason': authority_reason, 'parameter_provenance': links, 'action': data['action'], 'params': data['params'],
               'token_digest': digest(token), 'claims': claims, 'accountability': state['accountability']}
        row['classification'] = classify(row)
        signals = {**row, 'classification': row['classification']}
        response = response_for(signals, 'PAA' if state['condition'] in ('C-PAA-002', 'C-PAA-B-002') else 'authority-only')
        # C0/C1 are identity-only baselines: record authority/signal assessment but do not enforce it.
        enforce = state['condition'] in ('C2-002', 'C3-9449-002', 'C-PAA-002', 'C-PAA-B-002')
        if not enforce:
            response = 'observe_only'
        if enforce and response in ('suspend_identity', 'contain_identity'):
            state['suspended'] = True
            state['revoked'].add(digest(token))
            if claims.get('actor_svid_digest'):
                state['blocked_svid_digests'].add(claims['actor_svid_digest'])
        if enforce and response == 'revoke_credential':
            state['revoked'].add(digest(token))
            if claims.get('actor_svid_digest'):
                state['blocked_svid_digests'].add(claims['actor_svid_digest'])
        flagged = state.setdefault('flagged_inputs', {})
        if enforce and response == 'deny_keep_identity_flag_input':
            for link in links:
                if not link.get('already_in_principal_intent', False):
                    flagged[link['content_hash']] = {'source_request_id':link['source_request_id'],
                        'content_hash':link['content_hash'],'trigger_request_id':request_id}
        row['input_flagged'] = enforce and response == 'deny_keep_identity_flag_input' and any(link['content_hash'] in flagged for link in links)
        allowed = possession_valid and not state['suspended'] and digest(token) not in state['revoked'] and (allowed_authority or not enforce)
        if enforce and state['accountability'] == 'tamper':
            allowed = False
        result = None
        outcome = 'denied'
        if request_id in state['cache']:
            old = state['cache'][request_id]
            if old['fingerprint'] != fingerprint:
                raise HTTPException(409, 'idempotency conflict')
            if allowed:
                result, outcome = old['result'], 'duplicate'
        elif allowed:
            url = TOOLS[data['action'].split('.')[0]]
            effect = await HTTP.post(url + '/execute', json={k: data[k] for k in ('run_id', 'request_id', 'action', 'params')})
            if 400 <= effect.status_code < 500:
                result = {'error': 'synthetic_application_rejected_request', 'http_status': effect.status_code}
                outcome = 'tool_error'
            else:
                effect.raise_for_status()
                result = effect.json()
                outcome = 'executed'
                state['counters']['records'] += result.get('records', 0)
                state['counters']['payment'] += result.get('amount', 0)
                intent = intent_key({'action': data['action'], 'params': data['params']})
                state['counters']['intents'][intent] = state['counters']['intents'].get(intent, 0) + 1
                state['cache'][request_id] = {'fingerprint': fingerprint, 'result': result, 'token_digest': digest(token)}
                if data['action'] in ('files.read', 'email.read', 'crm.read'):
                    text = canonical(result.get('result'))
                    state['provenance'].append({'text': text, 'content_hash': digest(text), 'request_id': request_id})
        row.update(response_action=response, outcome=outcome, suspended=state['suspended'],
                   credential_revoked=digest(token) in state['revoked'], reason=reason if not possession_valid else authority_reason,
                   counters=copy.deepcopy(state['counters']))
        row = append(state, row)
        return {'allowed': allowed, 'outcome': outcome, 'result': result, 'audit': row,
                'dpop_required': state['condition'] in ('C3-9449-002', 'C-PAA-B-002'),
                'checkpoint': {'count': len(state['audit']), 'hash': row['hash']},
                'authorization_ms': (time.perf_counter() - started) * 1000}


@app.post('/admin/event')
async def event(request: Request):
    admin(request)
    data = await request.json()
    state = RUNS[data['run_id']]
    async with LOCKS[state['run_id']]:
        if data['event'] in ('gap', 'tamper'):
            state['accountability'] = data['event']
        elif data['event'] == 'revoke_actor':
            ISSUER.revoked.add(data['token_digest'])
        else:
            raise HTTPException(422)
    return {'ok': True, 'active_at': time.time()}


@app.post('/admin/truncated-test-token')
async def truncated_test_token(request: Request):
    """Signed malformed-chain positive control: trusted harness, not attacker API."""
    admin(request)
    data = await request.json()
    claims = copy.deepcopy(ISSUER.verify(data['token'], enforce_chain=False))
    claims['act'] = {'sub': claims['act']['sub']}
    return {'token': ISSUER._sign(claims)}


@app.post('/admin/recover')
async def recover(request: Request):
    admin(request)
    data = await request.json()
    state = RUNS[data['run_id']]
    # Old revoked tokens stay revoked. New root/capability is required; this endpoint
    # only clears containment after caller supplies a newly validated exchange.
    claims = ISSUER.verify(data['new_token'])
    if (claims['task'] != state['run_id'] or digest(data['new_token']) in state['revoked'] or
            claims.get('act', {}).get('sub') != state['actors']['A']['spiffe_id'] or
            not claims.get('actor_svid_digest') or claims['actor_svid_digest'] in state['blocked_svid_digests']):
        raise HTTPException(403)
    state['suspended'] = False
    state['accountability'] = 'complete'
    return {'recovered': True, 'claims': claims}


@app.get('/admin/evidence/{run_id}')
async def evidence(run_id: str, request: Request):
    admin(request)
    state = RUNS[run_id]
    independent = {}
    for name, url in TOOLS.items():
        response = await HTTP.get(url + '/evidence/' + run_id)
        response.raise_for_status()
        independent[name] = response.json()
    return {'audit': state['audit'], 'checkpoint': {'count': len(state['audit']), 'hash': state['audit'][-1]['hash'] if state['audit'] else '0' * 64},
            'independent': independent, 'suspended': state['suspended'], 'flagged_inputs': list(state.get('flagged_inputs', {}).values())}


@app.post('/admin/retire')
async def retire(request: Request):
    admin(request)
    data = await request.json()
    RUNS.pop(data['run_id'], None)
    LOCKS.pop(data['run_id'], None)
    return {'retired': True}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
