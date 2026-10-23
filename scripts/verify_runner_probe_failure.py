"""Prepare or run one explicitly controlled, namespace-scoped engineering fault.

No action without --execute. Execute only after research clearance and current
image deployment. No LLM calls, policy changes, global resets or automatic retry.
"""
from __future__ import annotations
import argparse,gzip,hashlib,inspect,json,re,sqlite3,subprocess,time,uuid
from pathlib import Path
from unittest.mock import patch


def apply_scoped_fault(connection, authorization):
    """Remove brief from exactly one proven baseline's run, using parameterized CAS."""
    if set(authorization)!={'run_id','baseline_request_id','expected_content_sha256','batch_name'}:
        raise ValueError('Unexpected fault authorization fields')
    run_id=authorization['run_id'];request_id=authorization['baseline_request_id']
    if not re.fullmatch(r'r[0-9a-f]{32}',run_id):raise ValueError('Invalid owned run ID')
    if not re.fullmatch(r'[0-9a-f]{32}',request_id):raise ValueError('Invalid baseline request ID')
    if not re.fullmatch(r'qa-runner-probe-failure-\d{8}T\d{6}Z-[0-9a-f]{8}',authorization['batch_name']):
        raise ValueError('Not a fresh helper-owned engineering batch')
    if not re.fullmatch(r'[0-9a-f]{64}',authorization['expected_content_sha256']):raise ValueError('Invalid content hash')
    connection.execute('BEGIN IMMEDIATE')
    try:
        row=connection.execute('SELECT state FROM runs WHERE run_id=?',(run_id,)).fetchone()
        baseline=connection.execute('SELECT fingerprint,response FROM calls WHERE run_id=? AND request_id=?',(run_id,request_id)).fetchone()
        if row is None or baseline is None:raise ValueError('Owned run/baseline absent')
        fingerprint=json.loads(baseline[0]);response=json.loads(baseline[1])
        if fingerprint!={'action':'files.read','params':{'path':'brief'}} or response.get('ok') is not True:
            raise ValueError('Baseline is not a committed brief read')
        before=json.loads(row[0]);after=json.loads(row[0]);brief=before.get('files',{}).get('brief')
        if not isinstance(brief,str) or response.get('result',{}).get('path')!='brief' or response['result'].get('content')!=brief:
            raise ValueError('Baseline does not match current brief')
        if hashlib.sha256(brief.encode('utf-8')).hexdigest()!=authorization['expected_content_sha256']:
            raise ValueError('Brief content hash mismatch')
        del after['files']['brief']
        updated=json.dumps(after,sort_keys=True,separators=(',',':'))
        changed=connection.execute('UPDATE runs SET state=? WHERE run_id=? AND state=?',(updated,run_id,row[0])).rowcount
        if changed!=1:raise ValueError('Fault CAS must affect exactly one row')
        connection.commit()
        return {'run_id':run_id,'baseline_request_id':request_id,'rows_updated':changed,'before':before,'after':after,
          'before_state_sha256':hashlib.sha256(row[0].encode('utf-8')).hexdigest(),
          'after_state_sha256':hashlib.sha256(updated.encode('utf-8')).hexdigest(),
          'mutation':'Only files.brief removed from this fresh namespace; calls/audit/policy untouched'}
    except Exception:
        connection.rollback();raise


def ordered_rows(folder,stem):
    paths=sorted(folder.glob(stem+'*.jsonl.gz'),key=lambda p:(p.name!=stem+'.jsonl.gz',p.name))
    for p in paths:
        with gzip.open(p,'rt',encoding='utf-8') as f:
            for line in f:yield json.loads(line)


def execute():
    from testbed import runner
    from testbed.common import ROOT,canonical,write_json
    from testbed.audit import verify as verify_audit
    from analysis.cli import verify_raw
    from scripts.tool_evidence import snapshot
    import httpx
    # A real idle gate precedes any Docker query or creation of a run namespace.
    with httpx.Client(timeout=5,trust_env=False) as client:
        health=client.get('http://127.0.0.1:8767/health');health.raise_for_status();health=health.json()
    if health.get('active_runs')!=0:raise RuntimeError('Active PA tasks: research/live clearance not satisfied')
    paths=['testbed/probe.py','testbed/client.py','testbed/service.py','testbed/runner.py']
    expected={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    program='import hashlib,json,pathlib;print(json.dumps({p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in '+repr(paths)+'}))'
    deployed={}
    for service in ['attacker','pa']:
        p=subprocess.run(['docker','compose','exec','-T',service,'python','-c',program],cwd=ROOT,capture_output=True,text=True,timeout=20,check=True)
        deployed[service]=json.loads(p.stdout)
    if any(actual!=expected for actual in deployed.values()):raise RuntimeError('Deploy current prospective image first; source mismatch')
    name='qa-runner-probe-failure-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:8]
    batch=ROOT/'results'/name;batch.mkdir(parents=True,exist_ok=False)
    config={'mode':'scripted','phase':'engineering','conditions':['C0'],'scenarios':['S4'],'repeats':1,
      'ttl_seconds':[300],'revocation_modes':['expiry'],'seed':603,'concurrency':1,'observation_seconds':2,
      'probe_interval_seconds':.1,'s3_probe_interval_seconds':10,'theft_delay_seconds':120,
      'study_kind':'controlled engineering fault, not research data','protocol_id':'qa-runner-probe-failure-v1'}
    runner.validate_config(config);cell=runner.manifest(config)[0]
    write_json(batch/'config.json',config)
    write_json(batch/'manifest.json',{'collection_name':name,'cells':[cell],'count':1,'created_at':time.time(),
      'mode':'scripted','phase':'engineering','classification':'Explicit controlled namespace-only failure; no LLM or research replicate'})
    started=time.time();ledger=ROOT/'.runtime/spend.sqlite'
    ledger_before=hashlib.sha256(ledger.read_bytes()).hexdigest() if ledger.exists() else None
    evidence={'classification':'Postcollection engineering fault, no paid calls/research observations','started_at':started,
      'source_sha256':expected,'deployed_sha256':deployed,'provider_calls':0,'fault_injected':False,'checks':{},'passed':False}
    evidence['helper_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    real_request=runner.container_request

    def request_with_owned_fault(container,data):
        result=real_request(container,data)
        call=data.get('data') or {}
        if container!='attacker' or call.get('action')!='files.read' or call.get('params')!={'path':'brief'}:
            return result
        if evidence['fault_injected']:raise RuntimeError('Unexpected second baseline; fault is never repeated')
        run_id=call.get('run_id','');folder=batch/'runs'/run_id
        if not re.fullmatch(r'r[0-9a-f]{32}',run_id) or not folder.resolve().is_relative_to((batch/'runs').resolve()):
            raise RuntimeError('Fault target escapes fresh engineering namespace')
        own=list((batch/'runs').iterdir())
        if len(own)!=1 or own[0]!=folder:raise RuntimeError('Batch must own exactly this one new run')
        summary=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
        if summary.get('status')!='running' or summary.get('metadata',{}).get('started_at',0)<started:
            raise RuntimeError('Target is not this new running unit')
        if any(summary.get(k)!=v for k,v in {**cell,'mode':'scripted','phase':'engineering'}.items()):
            raise RuntimeError('Target differs from authorized engineering cell')
        response=result.get('data',{});audit=response.get('audit',{})
        if result.get('status')!=200 or response.get('allowed') is not True or response.get('outcome')!='executed':
            raise RuntimeError('A real successful baseline must precede the fault')
        if audit.get('request_id')!=call.get('request_id'):raise RuntimeError('Baseline request identity mismatch')
        identity=json.loads((folder/'identity.json').read_text(encoding='utf-8'))
        if audit.get('credential_id')!=identity['credential_id']:raise RuntimeError('Baseline belongs to another identity')
        content=response['result']['result']['content']
        auth={'run_id':run_id,'baseline_request_id':call['request_id'],'expected_content_sha256':hashlib.sha256(content.encode('utf-8')).hexdigest(),'batch_name':name}
        write_json(batch/'baseline-response.json',{'call':call,'response':result})  # no bearer/header is included
        # Only parameterized SQL for this namespace. No reset or extra PA audit action.
        fault_program='import hashlib,json,re,sqlite3,sys,time\nfrom pathlib import Path\nfrom infra.tools import DB,KIND\n'+inspect.getsource(apply_scoped_fault)+'''
assert KIND=='files' and DB.resolve()==Path('/state/files.sqlite3') and DB.is_file(), 'Unexpected private tool database'
authorization=json.load(sys.stdin)
with sqlite3.connect('file:'+str(DB)+'?mode=rw',uri=True,timeout=30,isolation_level=None) as db:
 result=apply_scoped_fault(db,authorization)
result['fault_committed_at']=time.time()
print(json.dumps(result))
'''
        changed=subprocess.run(['docker','compose','exec','-T','files','python','-c',fault_program],cwd=ROOT,
          input=canonical(auth),capture_output=True,text=True,timeout=40,check=True)
        record=json.loads(changed.stdout)
        if record.get('run_id')!=run_id or record.get('rows_updated')!=1:raise RuntimeError('Fault mutation receipt invalid')
        evidence['fault_injected']=True;evidence['run_id']=run_id
        write_json(batch/'fault-record.json',record)
        return result

    try:
        # The only host monkeypatch; real requests and the real child stream remain intact.
        with patch.object(runner,'container_request',request_with_owned_fault):
            summary=runner.run_one(cell,config,batch)
        folder=batch/'runs'/summary['run_id'];probes=list(ordered_rows(folder,'probes'))
        actions=list(ordered_rows(folder,'actions'));audits=list(ordered_rows(folder,'audit'))
        error_probe=probes[-1] if probes else {};last=actions[-1] if actions else {}
        baseline=json.loads((batch/'baseline-response.json').read_text(encoding='utf-8'))
        seals=verify_raw(batch);audit=verify_audit(audits,json.loads((folder/'checkpoint.json').read_text(encoding='utf-8')))
        independent=snapshot(summary['run_id']);write_json(batch/'independent-tool-evidence.json',independent)
        with httpx.Client(timeout=5,trust_env=False) as client:
            post_health=client.get('http://127.0.0.1:8767/health');post_health.raise_for_status();post_health=post_health.json()
        evidence['post_run_pa_health']=post_health
        evidence['checks']={'fault_injected_once':evidence['fault_injected'],
          'host_explicit_measurement_failure':summary.get('probe_measurement_error',{}).get('category')=='tool_failure',
          'expected_infrastructure_status':summary.get('status')=='infrastructure_failure',
          'no_false_event':summary.get('event_observed') is None and summary.get('first_denial_seconds') is None,
          'client_failure_preserved':error_probe.get('client_probe_classification')=='measurement_failure' and error_probe.get('client_probe_measurement_error',{}).get('category')=='tool_failure',
          'failed_probe_not_invalid_credential':error_probe.get('valid') is None and error_probe.get('credential_event') is False,
          'actual_allowed_tool_error':last.get('action')=='files.read' and last.get('allowed') is True and last.get('reason')=='valid' and last.get('outcome')=='tool_error',
          'actual_missing_file_error':last.get('result',{}).get('error')=='HTTPStatusError' and last.get('result',{}).get('effect_uncertain') is False,
          'no_added_pa_audit_between_baseline_and_failure':last.get('audit',{}).get('sequence')==baseline['response']['data']['audit']['sequence']+1,
          'audit_chain_checkpoint_valid':audit['valid'],'raw_seals_valid':seals['valid'],
          'fault_state_independently_preserved':'brief' not in independent['files']['state']['files'],
          'run_retirement_succeeded':not (folder/'retirement-error.json').exists(),
          'actual_pa_idle_after_retirement':post_health.get('role')=='pa' and post_health.get('active_runs')==0}
        evidence['raw_verification']=seals;evidence['audit_verification']=audit
        write_json(batch/'expected-failed-summary.json',summary)
        evidence['passed']=all(evidence['checks'].values())
    except Exception as error:
        evidence['error_type']=type(error).__name__
        raise
    finally:
        evidence['finished_at']=time.time()
        evidence['spend_ledger_unchanged']=ledger_before==(hashlib.sha256(ledger.read_bytes()).hexdigest() if ledger.exists() else None)
        evidence['passed']=evidence['passed'] and evidence['spend_ledger_unchanged']
        write_json(batch/'verification.json',evidence)
        write_json(batch/'batch-status.json',{'planned':1,'original_failures':1,'reruns':0,
          'remaining_failures':1,'completed_at':time.time(),'intentional_negative_control':True,
          'verification_passed':evidence['passed'],'provider_calls':0,
          'reason':'Controlled engineering tool failure; expected infrastructure_failure retained, not research data'})
    print(json.dumps({'output':str(batch),'passed':evidence['passed'],'provider_calls':0,'expected_unit_status':'infrastructure_failure'}))
    return 0 if evidence['passed'] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if not args.execute:
        print(json.dumps({'prepared_only':True,'requires':'Lead clearance after research, idle PA, current deployed image','paid_calls':0,'fault_executed':False}));return 0
    return execute()


if __name__=='__main__':raise SystemExit(main())
