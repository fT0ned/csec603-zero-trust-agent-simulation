import gzip
import hashlib
import json
import pytest
from scripts import adjudicate_credential_endpoints as audit


def fixture(tmp_path, monkeypatch, outcome='tool_error', mode='expiry', signals=None):
    monkeypatch.setattr(audit,'ROOT',tmp_path)
    folder=tmp_path/'runs'/'r1';folder.mkdir(parents=True)
    summary={'run_id':'r1','condition':'C0' if signals is None else 'C2','scenario':'S4',
        'revocation_mode':mode,'security_decision_at':1.5,'event_observed':True,'status':'completed'}
    (folder/'summary.json').write_text(json.dumps(summary))
    good={'client':'attacker','action':'files.read','params':{'path':'brief'},'allowed':True,'outcome':'executed','reason':'valid'}
    terminal={**good,'allowed':outcome=='tool_error','outcome':outcome,'audit':{'runtime_signals':signals} if signals else {}}
    for name,rows in {'actions.jsonl.gz':[good],'actions-0007.jsonl.gz':[terminal],
        'probes.jsonl.gz':[{'valid':True,'reason':'valid','time':1,'elapsed_seconds':1}],
        'probes-0001.jsonl.gz':[{'valid':False,'reason':'valid','time':2,'elapsed_seconds':2}]}.items():
        (folder/name).write_bytes(gzip.compress(('\n'.join(json.dumps(row) for row in rows)+'\n').encode()))
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
    (folder/'raw-manifest.json').write_text(json.dumps({'hash_scheme':'sha256-bytes','files':files}))
    return folder


def test_rotated_terminal_tool_error_is_not_expiry_or_silent_survival_censor(tmp_path, monkeypatch):
    row=audit.audit_run(fixture(tmp_path,monkeypatch),{})
    assert row['terminal_category']=='allowed_but_tool_failed_not_credential_denial'
    assert row['issues'] and not row['credential_denial_observed'] and not row['access_denial_observed']
    assert row['candidate_sensitivity_censor_seconds']==1
    assert 'informative' in row['interpretation']
    assert row['terminal_action_path'].endswith('actions-0007.jsonl.gz')


def test_pa_revocation_race_is_access_denial_not_jwt_expiry(tmp_path, monkeypatch):
    signals={'revoked':True,'suspended':False,'credential_valid':True}
    row=audit.audit_run(fixture(tmp_path,monkeypatch,'denied','now',signals),{})
    assert not row['issues'] and row['access_denial_observed']
    assert not row['credential_denial_observed']


def test_stale_reason_without_declared_revocation_is_unresolved(tmp_path, monkeypatch):
    row=audit.audit_run(fixture(tmp_path,monkeypatch,'denied','expiry'),{})
    assert row['issues'] and not row['access_denial_observed']


def test_altered_raw_cannot_enter_semantic_review(tmp_path, monkeypatch):
    folder=fixture(tmp_path,monkeypatch)
    (folder/'probes-0001.jsonl.gz').write_bytes(gzip.compress(b'{}\n'))
    with pytest.raises(ValueError,match='hash mismatch'):audit.audit_run(folder,{})
