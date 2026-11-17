import asyncio
import copy

import httpx
from fastapi.testclient import TestClient

from testbed.extension import service
from testbed.extension.fixtures import fixture


def test_missing_application_resource_is_a_tool_error_not_infrastructure(monkeypatch, tmp_path):
    fixed = fixture('benign', 1, 'crm-handoff')
    state = {'run_id': 'r', 'condition': 'C0-E', 'strategy': 'PAA', 'delegation': fixed['delegation'],
             'actors': {'A': {'origin': 'testclient'}}, 'static': 'synthetic-test-token', 'audit': [],
             'provenance': [], 'counters': {'records': 0, 'payment': 0, 'intents': {}}, 'suspended': False,
             'revoked': set(), 'accountability': 'complete', 'cache': {}}
    class MissingTool:
        async def post(self, url, **kwargs):
            return httpx.Response(404, request=httpx.Request('POST', url), json={'detail': 'No such synthetic file'})
    monkeypatch.setattr(service, 'ADMIN', 'test-admin')
    monkeypatch.setattr(service, 'STATE', tmp_path)
    monkeypatch.setattr(service, 'RUNS', {'r': state})
    monkeypatch.setattr(service, 'LOCKS', {'r': asyncio.Lock()})
    monkeypatch.setattr(service, 'HTTP', MissingTool())
    client = TestClient(service.app)
    response = client.post('/internal/execute', headers={'x-admin-secret': 'test-admin'}, json={
        'run_id': 'r', 'request_id': 'request', 'action': 'files.read', 'params': {'path': 'brief.md'},
        '_peer': 'testclient', '_authorization': ['Bearer synthetic-test-token'], '_proofs': [], '_url': 'http://pep/tool'})
    assert response.status_code == 200
    assert response.json()['outcome'] == 'tool_error'
    assert response.json()['allowed'] is True  # authorization succeeds, application rejects
    assert response.json()['result']['http_status'] == 404
    assert state['counters'] == {'records': 0, 'payment': 0, 'intents': {}}
    assert state['provenance'] == []
