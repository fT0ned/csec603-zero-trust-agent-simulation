import asyncio
import copy
from unittest.mock import patch
from fastapi.testclient import TestClient
from testbed import service
from testbed.common import digest
from tests.test_service_failures import FakeHTTP
from testbed.fixtures import fixture


def test_append_record_does_not_retain_mutable_context(tmp_path):
    state = {'records': [], 'audit_count': 0}
    context = {'workflow': {'records': 0}}
    row = {'policy_input': context}
    with patch.object(service, 'STATE', tmp_path):
        service.append_record('snapshot', state, row)
    original = copy.deepcopy(state['records'][0])
    context['workflow']['records'] = 100
    row['policy_input']['extra'] = True
    assert state['records'][0] == original
    hashed = dict(original); claimed = hashed.pop('hash')
    assert digest(hashed) == claimed


def test_later_exports_preserve_prior_policy_input_and_hash(tmp_path):
    state = {'condition': 'C2', 'credential_id': 'digest', 'spiffe_id': 'spiffe://test/agent',
             'delegation': fixture('S5', 604)['delegation'], 'workflow': {'records': 0, 'payment': 0},
             'suspended': False, 'revoked': False, 'cache': {}, 'records': [], 'audit_count': 0,
             'grants': {}, 'provenance': [], 'expected_origin': 'agent'}
    with patch.object(service, 'ROLE', 'pa'), patch.object(service, 'ADMIN', 'test-control'), \
         patch.object(service, 'HTTP', FakeHTTP('success')), patch.object(service, 'STATE', tmp_path), \
         patch.dict(service.RUNS, {'snapshot': state}), \
         patch.dict(service.LOCKS, {'snapshot': asyncio.Lock()}):
        with TestClient(service.app) as client:
            results = []
            for i in range(2):
                results.append(client.post('/control/snapshot/execute', headers={'x-admin-secret': 'test-control'}, json={
                    'run_id': 'snapshot', 'request_id': str(i), 'action': 'crm.export',
                    'params': {'offset': 5*i, 'limit': 5}, 'origin': 'agent',
                    'credential_valid': True, 'credential_reason': 'valid'}).json())
            assert state['workflow']['records'] == 10
            assert [r['policy_input']['workflow']['records'] for r in state['records']] == [0, 5]
            assert state['records'] == [r['audit'] for r in results]
            for row in state['records']:
                hashed = dict(row); claimed = hashed.pop('hash')
                assert digest(hashed) == claimed
