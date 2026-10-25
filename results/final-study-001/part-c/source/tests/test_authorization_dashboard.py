import json
from dashboard.app import create_app
from fastapi.testclient import TestClient


def test_objective_study_is_separate_and_uses_independent_commit_counters(tmp_path):
    root = tmp_path / 'results' / 'agent-authorization-pilot-001'
    run = root / 'runs' / 'aa1'
    run.mkdir(parents=True)
    config = {'mode': 'llm', 'phase': 'pilot', 'protocol_id': 'agent-authorization-v1',
              'study_kind': 'objective-driven-authorization',
              'system_prompt_profile': 'operational-objective-v1'}
    (root / 'config.json').write_text(json.dumps(config))
    (root / 'manifest.json').write_text(json.dumps({'count': 1, 'cells': [
        {'condition': 'C2', 'scenario': 'workflow-export'}]}))
    (root / 'batch-status.json').write_text(json.dumps({'remaining_failures': 0}))
    summary = {**config, 'run_id': 'aa1', 'status': 'completed', 'condition': 'C2',
               'scenario': 'workflow-export', 'seed': 1, 'unauthorized_attempts': 2,
               'unauthorized_denied': 2, 'unauthorized_allowed': 0,
               'unauthorized_committed': 0, 'unauthorized_outcome': False,
               'committed_records': 10, 'false_denials': 0, 'evidence_valid': True}
    path = run / 'summary.json'
    path.write_text(json.dumps(summary))
    original = path.read_bytes()
    client = TestClient(create_app(tmp_path / 'results', repo=tmp_path), base_url='http://127.0.0.1:8765')
    job = client.get('/api/jobs').json()[0]
    assert job['evidence_label'] == 'REAL LLM'
    assert job['config']['phase'] == 'pilot'
    assert job['config']['system_prompt_profile'] == 'operational-objective-v1'
    observed = client.get('/api/jobs/agent-authorization-pilot-001/runs').json()[0]
    assert observed['harmful_attempts'] == 2 and observed['harmful_executed'] == 0
    assert observed['unauthorized_denied'] == 2 and observed['committed_records'] == 10
    assert path.read_bytes() == original
