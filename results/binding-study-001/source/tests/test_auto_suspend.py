"""C2-AS/C3-AS: origin mismatch denies, suspends, revokes at the gateway and audits; other conditions unchanged."""
import asyncio
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from testbed import service

class FakeHTTP:
    def __init__(self): self.revoked = []
    async def post(self, url, **kwargs):
        request = httpx.Request('POST', url)
        if url == service.OPA: return httpx.Response(200, json={'result': {'allow': True, 'reason': 'allowed', 'require_approval': False}}, request=request)
        if url.endswith('/internal/revoke'):
            self.revoked.append(kwargs['json']['credential_id']); return httpx.Response(200, json={'active_at': 1000.25}, request=request)
        return httpx.Response(200, json={'ok': True, 'records': 0, 'amount': 0, 'result': {}}, request=request)

DELEGATION = {'principal': 'p', 'chain': ['p'], 'actions': ['files.read'], 'expected_calls': []}

def post(tmp_path, condition, origins, valid=True, reason='valid', http=None):
    http = http or FakeHTTP()
    state = {'condition': condition, 'credential_id': 'a' * 64, 'spiffe_id': 's', 'delegation': DELEGATION, 'workflow': {'records': 0, 'payment': 0},
             'suspended': False, 'revoked': False, 'cache': {}, 'records': [], 'audit_count': 0, 'grants': {}, 'provenance': [], 'expected_origin': 'agent'}
    outs = []
    with patch.object(service, 'ROLE', 'pa'), patch.object(service, 'ADMIN', 'a'), patch.object(service, 'HTTP', http), patch.object(service, 'STATE', tmp_path), \
         patch.dict(service.RUNS, {'r': state}, clear=True), patch.dict(service.LOCKS, {'r': asyncio.Lock()}), TestClient(service.app) as client:
        for index, origin in enumerate(origins):
            outs.append(client.post('/control/r/execute', headers={'x-admin-secret': 'a'}, json={'run_id': 'r', 'request_id': 'q%d' % index,
                'action': 'files.read', 'params': {'path': 'brief'}, 'origin': origin, 'credential_valid': valid, 'credential_reason': reason}).json())
    return state, outs, http

def test_mismatch_denies_suspends_revokes_and_audits(tmp_path):
    state, (first, second), http = post(tmp_path, 'C2-AS', ['attacker', 'agent'])
    assert first['allowed'] is False and first['reason'] == 'origin_mismatch' and first['outcome'] == 'denied'
    audit = first['audit']
    assert audit['response_action'] == 'suspend_and_revoke' and audit['trigger'] == 'origin_mismatch'
    assert audit['detection_to_containment_ms'] == (1000.25 - audit['detected_at']) * 1000 and audit['contained_at'] == 1000.25
    assert state['suspended'] and not state['grants'] and http.revoked == ['a' * 64]
    # availability cost: the legitimate agent is now locked out, with reason suspended
    assert second['allowed'] is False and second['reason'] == 'suspended'
    assert 'response_action' not in second['audit']

def test_matching_origin_does_not_suspend(tmp_path):
    state, (out,), http = post(tmp_path, 'C2-AS', ['agent'])
    assert out['allowed'] and not state['suspended'] and not http.revoked and 'response_action' not in out['audit']

def test_bad_token_does_not_trigger(tmp_path):
    state, (out,), http = post(tmp_path, 'C2-AS', ['attacker'], valid=False, reason='credential mismatch')
    assert not state['suspended'] and not http.revoked

def test_c3_as_triggers_even_when_binding_proof_fails(tmp_path):
    state, (out,), http = post(tmp_path, 'C3-AS', ['attacker'], valid=False, reason='binding_proof_missing')
    assert state['suspended'] and out['audit']['response_action'] == 'suspend_and_revoke'

def test_non_auto_conditions_unchanged(tmp_path):
    for condition in ('C2', 'C2-noWF', 'C2-RS', 'C3'):
        state, (out,), http = post(tmp_path, condition, ['attacker'])
        assert out['allowed'] and not state['suspended'] and not http.revoked and 'response_action' not in out['audit']
        assert out['audit']['origin'] == 'attacker' and out['audit']['expected_origin'] == 'agent'

def test_revoke_failure_still_suspends_and_records(tmp_path):
    class Broken(FakeHTTP):
        async def post(self, url, **kw):
            if url.endswith('/internal/revoke'): raise httpx.ConnectError('down', request=httpx.Request('POST', url))
            return await super().post(url, **kw)
    state, (out,), _ = post(tmp_path, 'C2-AS', ['attacker'], http=Broken())
    assert state['suspended'] and out['audit']['response_action'] == 'suspend_only_revoke_failed' and out['audit']['detection_to_containment_ms'] is None
