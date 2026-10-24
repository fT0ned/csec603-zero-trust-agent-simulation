import contextlib
import io
import json
from unittest.mock import patch
import pytest
from testbed import client
from testbed.probe import classify_probe, ProbeMeasurementError


@pytest.mark.parametrize('status,payload', [
    (200, {'allowed': True, 'outcome': 'tool_error', 'reason': 'valid'}),
    (200, {'allowed': False, 'outcome': 'infrastructure_error', 'reason': 'policy_engine_unavailable'}),
    (200, {'allowed': False, 'outcome': 'denied', 'reason': 'scope denied'}),
    (200, {'allowed': False, 'outcome': 'denied', 'reason': 'valid'}),
    (503, {'error': 'unavailable'}), (200, None),
    (200, {'allowed': True, 'outcome': 'denied', 'reason': 'revoked'}),
])
def test_noncredential_failures_never_become_expiry(status, payload):
    with pytest.raises(ProbeMeasurementError): classify_probe(status, payload)


@pytest.mark.parametrize('reason', ['revoked', 'invalid or expired JWT-SVID'])
def test_actual_credential_denial_is_an_event(reason):
    assert classify_probe(200, {'allowed': False, 'outcome': 'denied', 'reason': reason}) == 'credential_denied'


def test_stream_preserves_tool_failure_and_stops_without_expiry_or_retry():
    request={'url':'http://unused','data':{},'probe':{'interval':.001,'window':10}}
    def response(outcome):
        return {'status':200,'time':100,'data':{'allowed':True,'outcome':outcome,'reason':'valid'}}
    output=io.StringIO()
    with patch.object(client.sys,'stdin',io.StringIO(json.dumps(request))), patch.object(client,'request',side_effect=[response('executed'),response('tool_error')]) as send, contextlib.redirect_stdout(output):
        client.main()
    rows=[json.loads(line) for line in output.getvalue().splitlines()]
    assert send.call_count == 2
    assert rows[0]['probe_classification']=='valid'
    assert rows[1]['probe_classification']=='measurement_failure'
    assert rows[1]['probe_measurement_error']['category']=='tool_failure'
    assert rows[1]['data']['allowed'] is True
