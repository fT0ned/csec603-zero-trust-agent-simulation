"""Offline SQLite fixtures for the explicitly scoped live-QA fault helper."""
import hashlib,json,sqlite3
import pytest
from scripts.verify_runner_probe_failure import apply_scoped_fault


@pytest.fixture
def scope():
    db=sqlite3.connect(':memory:',isolation_level=None)
    db.execute('CREATE TABLE runs(run_id TEXT PRIMARY KEY,state TEXT NOT NULL)')
    db.execute('CREATE TABLE calls(run_id TEXT,request_id TEXT,fingerprint TEXT,response TEXT)')
    run='r'+'1'*32;other='r'+'2'*32;request='3'*32
    state={'files':{'brief':'synthetic content','public':'keep'},'exports':[],'payments':[]}
    for rid in [run,other]:db.execute('INSERT INTO runs VALUES (?,?)',(rid,json.dumps(state)))
    fingerprint={'action':'files.read','params':{'path':'brief'}}
    response={'ok':True,'result':{'path':'brief','content':'synthetic content'}}
    db.execute('INSERT INTO calls VALUES (?,?,?,?)',(run,request,json.dumps(fingerprint),json.dumps(response)))
    auth={'run_id':run,'baseline_request_id':request,
      'expected_content_sha256':hashlib.sha256(b'synthetic content').hexdigest(),
      'batch_name':'qa-runner-probe-failure-20261023T185600Z-1234abcd'}
    yield db,auth,other
    db.close()


def test_only_owned_row_brief_changes_and_baseline_ledger_remains(scope):
    db,auth,other=scope
    other_before=db.execute('SELECT state FROM runs WHERE run_id=?',(other,)).fetchone()[0]
    calls_before=db.execute('SELECT * FROM calls').fetchall()
    record=apply_scoped_fault(db,auth)
    assert record['rows_updated']==1 and 'brief' in record['before']['files'] and 'brief' not in record['after']['files']
    assert record['after']['files']['public']=='keep'
    assert db.execute('SELECT state FROM runs WHERE run_id=?',(other,)).fetchone()[0]==other_before
    assert db.execute('SELECT * FROM calls').fetchall()==calls_before
    assert json.loads(db.execute('SELECT state FROM runs WHERE run_id=?',(auth['run_id'],)).fetchone()[0])==record['after']


@pytest.mark.parametrize('override',[
    {'run_id':"r'; DELETE FROM runs;--"},
    {'batch_name':'study-002'},
    {'baseline_request_id':'4'*32},
    {'expected_content_sha256':'0'*64},
])
def test_failed_guards_do_not_mutate_any_fixture_row(scope,override):
    db,auth,_=scope;before=db.execute('SELECT * FROM runs ORDER BY run_id').fetchall()
    with pytest.raises(ValueError):apply_scoped_fault(db,{**auth,**override})
    assert db.execute('SELECT * FROM runs ORDER BY run_id').fetchall()==before


def test_nonbrief_baseline_is_refused_without_mutation(scope):
    db,auth,_=scope
    db.execute('UPDATE calls SET fingerprint=? WHERE run_id=?',(json.dumps({'action':'files.read','params':{'path':'public'}}),auth['run_id']))
    before=db.execute('SELECT * FROM runs ORDER BY run_id').fetchall()
    with pytest.raises(ValueError):apply_scoped_fault(db,auth)
    assert db.execute('SELECT * FROM runs ORDER BY run_id').fetchall()==before
