"""Read-only endpoint semantics audit; separate reports, no original mutation.

python scripts/adjudicate_credential_endpoints.py
Streams every rotated probe file and inspects the final rotated action chunk.
The frozen client stops at its first non-executed probe, so the first recorded
denial must be the final probe/action. Any violation is reported unresolved.
"""
from __future__ import annotations
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def chunk_order(path):
    match=re.search(r'-(\d+)\.jsonl',path.name)
    return int(match.group(1)) if match else 0

def iter_rows(path):
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt',encoding='utf-8') as stream:
        for number,line in enumerate(stream,1):yield number,json.loads(line)

def classify(action):
    if action.get('allowed') is False and action.get('outcome')=='denied' and action.get('reason') in ['revoked','invalid or expired JWT-SVID','credential mismatch']:
        return 'observed_credential_denial'
    if action.get('allowed') is True and action.get('outcome')=='executed':return 'executed_credential_validity_probe'
    if action.get('allowed') is True and action.get('outcome')=='tool_error':return 'allowed_but_tool_failed_not_credential_denial'
    return 'noncredential_or_unresolved_terminal_outcome'

def audit_run(folder,sources):
    summary=read(folder/'summary.json');manifest=read(folder/'raw-manifest.json')
    def pin(path):
        actual=digest(path);sources[str(path.relative_to(ROOT))]=actual
        if manifest.get('hash_scheme')!='sha256-bytes' or manifest['files'].get(path.name)!=actual:raise ValueError('Selected raw byte hash mismatch: '+str(path))
    pin(folder/'summary.json')
    probes=sorted(folder.glob('probes*.jsonl*'),key=chunk_order)
    actions=sorted(folder.glob('actions*.jsonl*'),key=chunk_order)
    if not probes or not actions:raise ValueError('Missing probe/action artifacts')
    invalid=[];last=None;last_valid=None;count=0
    for path in probes:
        pin(path)
        for line,probe in iter_rows(path):
            count+=1;last={'path':str(path.relative_to(ROOT)),'line':line,**probe}
            if probe.get('valid') is False:invalid.append(last)
            elif probe.get('valid') is True:last_valid=last
    # All rotations are enumerated numerically. The terminal record may be in a
    # high numbered chunk; never inspect actions.jsonl.gz alone.
    terminal_path=actions[-1];pin(terminal_path);terminal=None;terminal_line=0
    for terminal_line,action in iter_rows(terminal_path):terminal=action
    if terminal is None or last is None:raise ValueError('Empty terminal evidence')
    if terminal.get('client')!='attacker' or terminal.get('action')!='files.read' or terminal.get('params')!={'path':'brief'}:
        raise ValueError('Final action is not the harmless credential probe')
    category=classify(terminal);issues=[]
    # Authentication and PA execution are separate requests. A revocation can
    # land between them: the PA rejects the request while retaining the earlier
    # authentication reason. This is an access denial, not a tool failure or
    # evidence that the JWT itself expired. C0/C1 omit runtime signals; their
    # interpretation additionally relies on the frozen PA equation and trusted
    # control plane (the collector never invokes suspension).
    signals=terminal.get('audit',{}).get('runtime_signals')
    if (terminal.get('allowed') is False and terminal.get('outcome')=='denied'
        and terminal.get('reason')=='valid' and summary.get('scenario')=='S4'
        and summary.get('revocation_mode')=='now'
        and isinstance(summary.get('security_decision_at'),(int,float))
        and last.get('time',0)>=summary['security_decision_at']
        and (signals is None or (signals.get('revoked') is True and signals.get('suspended') is False))):
        category='observed_PA_revocation_denial_stale_authentication_reason'
    if len(invalid)>1 or (invalid and invalid[0]!=last):issues.append('First recorded invalid probe is not uniquely terminal')
    if bool(invalid)!=(summary.get('event_observed') is True):issues.append('Summary event flag differs from probe records')
    if last.get('reason')!=terminal.get('reason'):issues.append('Terminal probe/action reason mismatch')
    if last.get('valid') is not (terminal.get('outcome')=='executed'):issues.append('Frozen probe-valid mapping differs from recorded action')
    denial_categories={'observed_credential_denial','observed_PA_revocation_denial_stale_authentication_reason'}
    if invalid and category not in denial_categories:issues.append('Recorded credential-denial endpoint is not an observed credential rejection')
    if not invalid and category!='executed_credential_validity_probe':issues.append('Terminal non-success without a recorded event')
    row={k:summary.get(k) for k in ['run_id','condition','scenario','ttl_seconds','revocation_mode','seed','pair_id','status',
        'event_observed','first_denial_seconds','last_success_seconds','observation_window_seconds','security_decision_at','theft_at']}
    row.update(probe_count=count,probe_chunks=len(probes),action_chunks=len(actions),terminal_category=category,
        terminal_probe=last,terminal_action_path=str(terminal_path.relative_to(ROOT)),terminal_action_line=terminal_line,
        terminal_action={k:terminal.get(k) for k in ['request_id','allowed','outcome','reason','result']},
        terminal_runtime_signals=terminal.get('audit',{}).get('runtime_signals'),issues=issues,
        credential_denial_observed=category=='observed_credential_denial',
        access_denial_observed=category in denial_categories,
        last_successful_probe=last_valid,
        candidate_sensitivity_censor_seconds=last_valid.get('elapsed_seconds') if last_valid else summary.get('last_success_seconds'),
        interpretation='Credential denial is unobserved after a competing tool failure; last successful probe is only a conservative observed lower bound. Failure-related censoring may be informative; no KM/log-rank repair or validity acceptance is inferred.' if invalid and category not in denial_categories else 'Access endpoint consistent with terminal observation; stale valid reason on S4-now denotes PA revocation race, not JWT expiry. Existing clock/timing-quality limitations remain separate.')
    return row

def write_json(path,data):path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def main():
    original=ROOT/'results/study-002';out=ROOT/'results/quality-study002';out.mkdir(exist_ok=True)
    sources={};rows=[];failures=[]
    for i,path in enumerate(sorted((original/'runs').glob('*/summary.json'))):
        summary=read(path)
        if summary.get('status')!='completed' or summary.get('scenario') not in ['S3','S4']:continue
        try:rows.append(audit_run(path.parent,sources))
        except Exception as error:failures.append({'run_id':summary.get('run_id'),'error':type(error).__name__+': '+str(error)})
        if len(rows)%100==0:print('Audited '+str(len(rows))+' completed original S3/S4 runs',flush=True)
    affected=[r for r in rows if r['issues']]
    errors=[{'run_id':r['run_id'],'cell':{k:r[k] for k in ['condition','scenario','ttl_seconds','revocation_mode','seed']},
             'errors':r['issues'],'terminal_category':r['terminal_category']} for r in affected]+failures
    report={'passed':not errors,'scope':'credential-validity endpoint semantics','collection':'study-002',
        'collection_id':'study-002','collection_path':'results/study-002',
        'audit_complete':len(rows)==810 and not failures,'completed_S3_S4_audited':len(rows),
        'affected_count':len(affected),'errors':errors,'terminal_categories':dict(Counter(r['terminal_category'] for r in rows)),
        'affected_runs':affected,'all_run_records_file':'endpoint-run-index.json',
        'source_hashes_file':'source-hashes.json','helper_sha256':digest(Path(__file__)),
        'source_preservation':'Read-only audit; original raw summaries, probes, action chunks and analysis are unchanged.',
        'quality_boundary':'No acceptance of original timing findings or amendment. No inferential reanalysis. Failure-related early stopping may be informative censoring and cannot be silently converted to a valid ordinary survival event/censor.'}
    write_json(out/'quality-adjudication.json',report);write_json(out/'endpoint-run-index.json',rows);write_json(out/'source-hashes.json',sources)
    fields=['run_id','condition','scenario','ttl_seconds','revocation_mode','seed','event_observed','first_denial_seconds','terminal_category','credential_denial_observed','candidate_sensitivity_censor_seconds','issues']
    with (out/'endpoint-run-index.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for row in rows:writer.writerow({k:json.dumps(row[k]) if isinstance(row[k],list) else row[k] for k in fields})
    repair_root=ROOT/'results/timing-repair-001'
    repair_sources={};repair_rows=[];repair_failures=[]
    for folder in sorted((repair_root/'runs').iterdir()):
        try:repair_rows.append(audit_run(folder,repair_sources))
        except Exception as error:repair_failures.append({'run_id':folder.name,'error':str(error)})
    bad=[r for r in repair_rows if r['issues']]
    repair_report={'passed':not bad and not repair_failures,'scope':'credential-validity endpoint semantics',
        'collection_id':repair_root.name,'collection_path':'results/'+repair_root.name,
        'audit_complete':len(repair_rows)==31 and not repair_failures,'completed_S3_S4_audited':len(repair_rows),
        'errors':[{'run_id':r['run_id'],'errors':r['issues'],'terminal_category':r['terminal_category']} for r in bad]+repair_failures,
        'affected_runs':bad,'terminal_categories':dict(Counter(r['terminal_category'] for r in repair_rows)),
        'quality_boundary':report['quality_boundary'],'helper_sha256':digest(Path(__file__))}
    write_json(repair_root/'quality-adjudication.json',repair_report)
    review=ROOT/'results/repair-endpoint-review';review.mkdir(exist_ok=True)
    write_json(review/'endpoint-run-index.json',repair_rows);write_json(review/'source-hashes.json',repair_sources)
    print(json.dumps({'original_audited':len(rows),'original_affected':len(affected),'original_read_errors':len(failures),
        'repair_audited':len(repair_rows),'repair_affected':len(bad),'repair_read_errors':len(repair_failures)}),flush=True)

if __name__=='__main__':main()
