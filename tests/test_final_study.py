import json
from pathlib import Path

import pytest

from testbed import final_study as fs
from testbed.probe import ProbeMeasurementError, classify_probe, VALID, CREDENTIAL_DENIED

ROOT = Path(__file__).resolve().parents[1]
FULL = json.loads((ROOT / 'configs' / 'final-study.json').read_text(encoding='utf-8'))
PILOT = json.loads((ROOT / 'configs' / 'final-study-pilot.json').read_text(encoding='utf-8'))


def test_full_cell_counts_are_exact():
    counts = {p: len(c) for p, c in fs.expected_counts(FULL).items()}
    assert counts == {'A': 2100, 'B': 840, 'C': 150}
    a = fs.expected_counts(FULL)['A']
    by = {}
    for c in a: by[(c['condition'], c['scenario'])] = by.get((c['condition'], c['scenario']), 0) + 1
    assert by[('C3', 'S1')] == 30 and by[('C3-AS', 'S3')] == 90 and by[('C3-AS', 'S4')] == 180
    assert ('C3', 'S2') not in by and ('C2-AS', 'S5') not in by and ('C2-noWF', 'S3') not in by
    assert by[('C2-noWF', 'S2')] == 30 and by[('C2-RS', 'S5')] == 30


def test_part_b_has_28_cells_with_new_positive_controls_only():
    cells = fs.expected_counts(PILOT)['B']
    keys = {(c['condition'], c['scenario']) for c in cells}
    assert len(keys) == 28
    assert {s for c, s in keys if c in ('C2-AS', 'C3')} == {'positive-export', 'positive-payment'}


def test_pilot_is_two_repeats_short_ttl():
    counts = {p: len(c) for p, c in fs.expected_counts(PILOT).items()}
    assert counts == {'A': 68, 'B': 56, 'C': 10}
    assert {c['ttl_seconds'] for c in fs.expected_counts(PILOT)['A']} == {300, 900}  # 900 only for non-replay scenarios


def test_manifest_deterministic_and_seed_recorded():
    assert fs.expected_counts(FULL)['A'] == fs.expected_counts(FULL)['A'] and FULL['seed'] == 7603


def test_part_configs_are_isolated_and_monotonic():
    for p in 'ABC':
        c = fs.part_config(FULL, p)
        assert c['final_study'] and c['monotonic_timing'] and c['model'] == 'deepseek-flash' and c['seed'] == 7603


def test_validate_rejects_other_model_and_missing_monotonic():
    bad = dict(PILOT, model='gpt-4.1-mini-2025-04-14')
    with pytest.raises(ValueError): fs.validate_config(bad)
    with pytest.raises(ValueError): fs.validate_config(dict(PILOT, monotonic_timing=False))


def test_full_requires_freeze_binding():
    with pytest.raises(Exception): fs.validate_freeze(dict(FULL, repeats=29))


def _samples(offsets):
    return [{'wall_time': 1000 + i + o, 'monotonic_low': 50 + i, 'monotonic_high': 50 + i} for i, o in enumerate(offsets)]


def test_detect_step_flags_only_large_jumps():
    steps, clock = fs.detect_steps(_samples([0, 0.001, 0.002, 2.0, 2.001]))
    assert len(steps) == 1 and abs(steps[0]['offset_change_seconds'] - 1.998) < 1e-6
    assert fs.detect_steps(_samples([0, 0.01, 0.02, 0.03]))[0] == []


def test_flag_runs_by_timestamps_only(tmp_path):
    a = tmp_path / 'part-a' / 'runs'
    for rid, start, end, scen in (('r1', 100, 400, 'S3'), ('r2', 100, 400, 'S1'), ('r3', 900, 1000, 'S4')):
        (a / rid).mkdir(parents=True)
        (a / rid / 'summary.json').write_text(json.dumps({'run_id': rid, 'condition': 'C2', 'scenario': scen, 'ttl_seconds': 300,
                                                          'revocation_mode': 'none', 'seed': 1, 'metadata': {'started_at': start, 'finished_at': end}, 'status': 'completed',
                                                          'unauthorized_outcome': True}))
    flagged = fs.flag_runs(tmp_path, [{'between_wall_times': [200, 201], 'offset_change_seconds': 2.0}])
    assert [f['run_id'] for f in flagged] == ['r1']  # S1 is not a timing run; r3 outside the step


def test_probe_extended_classification_only_for_new_conditions():
    denied = {'outcome': 'denied', 'allowed': False, 'reason': 'binding_proof_missing'}
    with pytest.raises(ProbeMeasurementError): classify_probe(200, denied)
    assert classify_probe(200, denied, True) == CREDENTIAL_DENIED
    assert classify_probe(200, {'outcome': 'executed', 'allowed': True, 'reason': 'ok'}, True) == VALID
    with pytest.raises(ProbeMeasurementError): classify_probe(200, {'outcome': 'denied', 'allowed': False, 'reason': 'task_scope'}, True)


def test_old_conditions_cells_unchanged_by_new_conditions():
    from testbed import runner
    orig = {'conditions': ['C0', 'C1', 'C2', 'C2-noWF', 'C2-RS'], 'scenarios': ['S1', 'S2', 'S3', 'S4', 'S5'], 'ttl_seconds': [300, 900, 3600],
            'repeats': 30, 'seed': 603}
    assert len(runner.manifest(orig)) == 1200


def test_container_request_uses_utf8_for_non_ascii_model_text(monkeypatch):
    # Regression (found in the first pilot attempt): Windows text mode encoded an em dash as cp1252 0x97, which the
    # container decoded as a lone surrogate and the gateway answered HTTP 500.
    from testbed import runner
    seen = {}

    class Done:
        returncode = 0
        stdout = '{"status":200,"data":{}}'
        stderr = ''

    def fake(cmd, **kw):
        seen.update(kw); return Done()
    monkeypatch.setattr(runner.subprocess, 'run', fake)
    runner.container_request('agent-client', {'x': 'a \u2014 b'})
    assert seen['encoding'] == 'utf-8' and seen['text'] is True


def test_combined_analysis_runs_on_pilot_collection(tmp_path):
    pilot = ROOT / 'results' / 'final-study-pilot-001'
    if not (pilot / 'final-manifest.json').exists():
        pytest.skip('pilot collection not present')
    from analysis import final_study
    report = final_study.analyse(pilot, tmp_path / 'analysis', 100)
    assert report['completeness']['part_a_complete'] and report['completeness']['part_b_complete'] and report['completeness']['part_c_complete']
    assert not report['completeness']['errors']
    assert (tmp_path / 'analysis' / 'comparative-analysis.md').exists()
    again = final_study.analyse(pilot, tmp_path / 'analysis2', 100)
    assert (tmp_path / 'analysis' / 'h-verdicts.csv').read_text() == (tmp_path / 'analysis2' / 'h-verdicts.csv').read_text()


def test_clock_monitor_writes_durably(tmp_path):
    import time
    path = tmp_path / 'clock.jsonl'
    with fs.ClockMonitor(path):
        time.sleep(1.3)
    lines = path.read_text().splitlines()
    assert len(lines) >= 2 and 'wall_time' in json.loads(lines[0])


def test_resume_and_infrastructure_rerun_selection(tmp_path):
    cells = fs.expected_counts(PILOT)['C']
    d = tmp_path / 'part-c' / 'runs'
    def put(name, cell, status, **extra):
        (d / name).mkdir(parents=True)
        (d / name / 'summary.json').write_text(json.dumps({**cell, 'run_id': name, 'status': status, **extra}))
    put('r1', cells[0], 'completed'); put('r2', cells[1], 'infrastructure_failure'); put('r3', cells[2], 'running')
    pending = {c['cell_id'] for c in fs.pending_cells('C', cells, tmp_path)}
    assert cells[0]['cell_id'] not in pending and cells[1]['cell_id'] in pending and cells[2]['cell_id'] in pending and len(pending) == len(cells) - 1
    redo = fs.infra_reruns('C', cells, tmp_path)
    assert {r['cell_id'] for r in redo} == {cells[1]['cell_id'], cells[2]['cell_id']} and all(r['rerun_of'] for r in redo)
    put('r4', cells[1], 'completed', rerun_of='r2')
    assert cells[1]['cell_id'] not in {r['cell_id'] for r in fs.infra_reruns('C', cells, tmp_path)}
