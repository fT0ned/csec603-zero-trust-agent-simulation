"""easyboard: loader handles each collection type and missing files; server is read-only."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from easyboard import data, server

def run(root, name, summary):
    folder = root / name / 'runs' / summary['run_id']; folder.mkdir(parents=True)
    (folder / 'summary.json').write_text(json.dumps(summary))

def build(tmp_path):
    for i, (cond, bad) in enumerate([('C1', True), ('C2', False), ('C2', False)]):
        run(tmp_path, 'study-002', {'run_id': 'a%d' % i, 'condition': cond, 'scenario': 'S4', 'status': 'completed', 'mode': 'llm', 'phase': 'full',
             'unauthorized_outcome': bad, 'task_outcome': 'completed', 'exposure_seconds': 180.0 if cond == 'C1' else 4.0, 'event_observed': True})
    run(tmp_path, 'study-002', {'run_id': 'failed', 'condition': 'C2', 'status': 'infrastructure_failure'})
    run(tmp_path, 'agent-authorization-study-001', {'run_id': 'p', 'condition': 'C2', 'scenario': 'positive-export', 'status': 'completed', 'mode': 'llm', 'positive_control': True})
    run(tmp_path, 'agent-authorization-study-001', {'run_id': 'q', 'condition': 'C0', 'scenario': 'scope-delete', 'status': 'completed', 'mode': 'llm', 'unauthorized_outcome': True})
    for i, cond in enumerate(('C1', 'C2-AS')):
        run(tmp_path, 'binding-study-001', {'run_id': 'b%d' % i, 'condition': cond, 'status': 'completed', 'mode': 'scripted', 'phase': 'full',
             'first_attacker_success': cond == 'C1', 'legit_task_completed': True, 'exposure_seconds': 200.0 if cond == 'C1' else 0.0, 'event_observed': True,
             'legit_after_attack_allowed': cond == 'C1', 'detection_to_containment_ms': None if cond == 'C1' else 3.5})
    (tmp_path / 'binding-study-001' / 'manifest.json').write_text(json.dumps({'phase': 'full', 'count': 2}))
    run(tmp_path, 'enforcement-stress-002', {'run_id': 'e', 'condition': 'C2', 'status': 'completed', 'mode': 'scripted', 'phase': 'engineering', 'unauthorized_outcome': False})
    (tmp_path / 'enforcement-stress-002' / 'runs' / 'junk').mkdir()  # run folder without summary.json

def test_loader_each_collection_type(tmp_path):
    build(tmp_path)
    s = data.get_study('study-002', tmp_path, ttl=0)
    assert s['runs_counted'] == 3 and s['runs_total'] == 4 and ('Real AI model', 'info') in [tuple(b) for b in s['badges']]
    by = {r['key']: r for r in s['conditions']}
    assert by['C1']['bad'] == 1 and by['C2']['bad'] == 0 and by['C1']['exposure_median'] == 180.0
    a = data.get_study('agent-authorization-study-001', tmp_path, ttl=0)
    assert a['runs_counted'] == 1 and a['conditions'][0]['bad'] == 1  # positive control excluded
    b = data.get_study('binding-study-001', tmp_path, ttl=0)
    row = {r['key']: r for r in b['conditions']}
    assert row['C1']['bad'] == 1 and row['C2-AS']['locked_out'] == 1 and row['C2-AS']['containment_ms_median'] == 3.5
    assert ('Scripted test', 'info') in [tuple(x) for x in b['badges']]
    assert data.get_study('enforcement-stress-002', tmp_path, ttl=0)['runs_counted'] == 1

def test_missing_files_and_unknown_study_are_graceful(tmp_path):
    s = data.get_study('binding-study-001', tmp_path, ttl=0)
    assert s['present'] is False and 'Not run' in s['takeaway']
    assert data.get_study('nope', tmp_path) is None
    o = data.overview(tmp_path)
    assert [x['id'] for x in o['studies']] == ['final-study-001', 'binding-study-001']
    (tmp_path / 'study-002').mkdir()  # folder without runs or manifest
    assert data.get_study('study-002', tmp_path, ttl=0)['runs_counted'] == 0

def snapshot(root): return sorted((str(p.relative_to(root)), p.stat().st_mtime_ns, p.stat().st_size) for p in root.rglob('*'))

def test_server_serves_and_never_writes(tmp_path):
    build(tmp_path); before = snapshot(tmp_path)
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.make_handler(tmp_path)); port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try:
        base = 'http://127.0.0.1:%d' % port
        page = urllib.request.urlopen(base + '/').read().decode()
        assert 'Zero Trust Results Dashboard' in page
        assert json.load(urllib.request.urlopen(base + '/api/overview'))['studies']
        assert json.load(urllib.request.urlopen(base + '/api/study/study-002'))['conditions']
        assert json.load(urllib.request.urlopen(base + '/api/glossary'))
        for method in ('POST', 'PUT', 'DELETE'):
            try: urllib.request.urlopen(urllib.request.Request(base + '/api/study/study-002', data=b'{}', method=method)); assert False
            except urllib.error.HTTPError as error: assert error.code == 405
        try: urllib.request.urlopen(base + '/../../etc/passwd'); assert False
        except urllib.error.HTTPError as error: assert error.code == 404
    finally: httpd.shutdown(); httpd.server_close()
    assert snapshot(tmp_path) == before

def test_free_port_skips_busy():
    import socket
    with socket.socket() as busy:
        busy.bind(('127.0.0.1', 0)); port = busy.getsockname()[1]
        assert server.free_port(port) != port


def test_final_study_is_main_and_merges_parts(tmp_path):
    root = tmp_path / 'final-study-001'
    (root).mkdir()
    (root / 'final-manifest.json').write_text(json.dumps({'phase': 'full', 'total': 5}))
    def put(part, rid, **s):
        d = root / part / 'runs' / rid; d.mkdir(parents=True)
        (d / 'summary.json').write_text(json.dumps({'run_id': rid, 'status': 'completed', 'mode': 'llm', 'phase': 'full', **s}))
    put('part-a', 'a1', condition='C0', scenario='S2', unauthorized_outcome=True)
    put('part-a', 'a2', condition='C3', scenario='S3', unauthorized_outcome=False, event_observed=True, exposure_seconds=0.0)
    put('part-a', 'a3', condition='C3', scenario='S3', unauthorized_outcome=True, event_observed=True, exposure_seconds=0.0)
    put('part-a', 'a3r', condition='C3', scenario='S3', unauthorized_outcome=False, event_observed=True, exposure_seconds=0.0, timing_rerun_of='a3')
    put('part-c', 'c1', condition='C3', cell_id='C3-00', first_attacker_success=False, legit_task_completed=True, event_observed=True)
    o = data.overview(tmp_path)
    assert o['studies'][0]['id'] == 'final-study-001' and o['studies'][0]['main'] is True and o['studies'][0]['planned'] == 5
    s = data.get_study('final-study-001', tmp_path, ttl=0)
    by = {r['key']: r for r in s['conditions']}
    assert s['runs_total'] == 4 and by['C3']['runs'] == 3 and by['C3']['bad'] == 0 and by['C0']['bad'] == 1  # replaced original not counted
    assert 'Stolen-ID replay with real AI (Part C)' in s['scenarios']
