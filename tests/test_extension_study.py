import json
from pathlib import Path
import sqlite3

import httpx

from testbed.agent import Budget
from testbed.extension import provider
from testbed.extension.study import cells, selection, fixed_for
from testbed.common import ROOT


def test_preregistered_manifest_and_seed_separation():
    config = json.loads((ROOT / 'configs/extension-study.json').read_text())
    pilot = cells(config, pilot=True)
    assert len(pilot) == 120
    assert len({r['cell_id'] for r in pilot}) == len(pilot)
    full = cells({**config, 'selected_strata': []})
    assert len(full) == 1450
    assert len({r['cell_id'] for r in full}) == len(full)
    assert not {r['seed'] for r in pilot} & {r['seed'] for r in full}
    assert {r['model'] for r in pilot} == set(provider.MODELS)
    for r in full:
        if r['experiment'] == 'E4-replay':
            fixed = fixed_for(r)
            assert fixed['workload'] == 'crm-handoff'
            assert fixed['delegation']['max_records'] == 10


def test_selection_same_integer_threshold_and_no_pooling(tmp_path):
    for i in range(5):
        p = tmp_path / 'runs' / str(i)
        p.mkdir(parents=True)
        row = {'model': provider.MODELS[-1], 'prompt': 'neutral-v1', 'family': 'task-aligned', 'cell_id': str(i),
               'status': 'completed', 'injection_followed': i < 2}
        (p / 'summary.json').write_text(json.dumps(row))
    chosen = selection(tmp_path)
    assert chosen['selected_strata'] == [{'model': provider.MODELS[-1], 'prompt': 'neutral-v1', 'family': 'task-aligned'}]
    p = tmp_path / 'runs/0/summary.json'
    row = json.loads(p.read_text())
    row['injection_followed'] = False
    p.write_text(json.dumps(row))
    assert selection(tmp_path)['selected_strata'] == []


def test_rate_limit_backoff_reserves_every_attempt(monkeypatch, tmp_path):
    monkeypatch.setenv('STUDY_BUDGET_USD', '25')
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-test-credential')
    waits = []
    monkeypatch.setattr(provider.time, 'sleep', waits.append)
    attempts = []
    class FakeClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            attempts.append(kwargs['json'])
            if len(attempts) == 1:
                return httpx.Response(429)
            return httpx.Response(200, json={'model': 'gpt-4.1-mini-2025-04-14',
                'usage': {'prompt_tokens': 10, 'completion_tokens': 1},
                'choices': [{'message': {'role': 'assistant', 'content': 'done'}, 'finish_reason': 'stop'}]})
    monkeypatch.setattr(provider.httpx, 'Client', FakeClient)
    budget = Budget(25, tmp_path / 'spend.sqlite')
    transcript = []
    result = provider.loop('synthetic task', lambda _: None, transcript, model=provider.MODELS[1], system_prompt='test', seed=1, budget=budget)
    assert result['status'] == 'completed'
    assert waits == [1]
    assert len(transcript) == 2
    with sqlite3.connect(budget.path) as db:
        assert db.execute('select state from spend order by id').fetchall() == [('reserved',), ('settled',)]
    assert 'synthetic-test-credential' not in json.dumps(transcript)
