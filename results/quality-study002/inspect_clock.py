"""Read existing timing evidence only; write new quality-review artifacts."""
import csv,datetime,gzip,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BATCH=ROOT/'results/study-002'
OUT=Path(__file__).parent
EVENT=1792707634.2048422
OLD=1792707636.2292457
rows=[json.loads(p.read_text()) for p in sorted(BATCH.glob('runs/*/summary.json'))]
fields=['run_id','condition','scenario','ttl_seconds','revocation_mode','seed','pair_id','theft_schedule_error_seconds']
invalid=[r for r in rows if abs(r.get('theft_schedule_error_seconds',0))>1]
scope=[r for r in rows if r['scenario'] in ('S3','S4') and r.get('credential_received_at',float('inf'))<EVENT<r.get('metadata',{}).get('finished_at',0)]
failed=[r for r in rows if r['status']=='infrastructure_failure']
with (OUT/'invalid-timing.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=fields+['prior_failure_same_cell']);w.writeheader()
    for r in invalid:
        same=[s['run_id'] for s in failed if all(s.get(k)==r.get(k) for k in fields[1:7])]
        w.writerow({**{k:r.get(k) for k in fields},'prior_failure_same_cell':';'.join(same)})
details=[]
for r in scope:
    p=BATCH/'runs'/r['run_id']/'probes.jsonl.gz'
    previous=None;count=0;negative=[];near=[];minimum=None;first=None;last=None
    with gzip.open(p,'rt') as f:
        for line in f:
            x=json.loads(line);count+=1
            if first is None:first=x
            last=x
            if previous is not None:
                delta=x['time']-previous['time']
                minimum=delta if minimum is None else min(minimum,delta)
                item={'previous_time':previous['time'],'time':x['time'],'delta_seconds':delta}
                if delta<0:negative.append(item)
                if EVENT-5<=x['time']<=OLD+20:near.append(item)
            previous=x
    details.append({**{k:r.get(k) for k in fields},'receipt_at':r.get('credential_received_at'),
       'theft_at':r.get('theft_at'),'finished_at':r['metadata']['finished_at'],
       'phase_at_clock_step':'probing' if r.get('theft_at',float('inf'))<EVENT else 'handoff_sleep',
       'probe_file_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'probe_count':count,
       'minimum_adjacent_epoch_delta_seconds':minimum,'negative_timestamp_jumps':negative,
       'probe_pairs_near_clock_event':near,'first_probe':first,'last_probe':last,
       'observation_window_monotonic_seconds':r.get('observation_window_seconds'),
       'last_probe_minus_theft_epoch_seconds':last['time']-r['theft_at'] if last else None})
evidence={'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope_rule':'S3/S4 receipt_at < Windows clock-step new epoch < finished_at; inspect all retained probe rows for this scope',
 'clock_step_new_epoch':EVENT,'clock_step_old_epoch':OLD,'clock_step_seconds':EVENT-OLD,
 'scope_count':len(details),'probing_at_step':sum(d['phase_at_clock_step']=='probing' for d in details),
 'sleeping_at_step':sum(d['phase_at_clock_step']=='handoff_sleep' for d in details),
 'runs_with_negative_probe_timestamps':sum(bool(d['negative_timestamp_jumps']) for d in details),'runs':details,
 'limitations':['Probe records retain client epoch time and elapsed derived from epoch subtraction; they do not retain independent client-monotonic timestamps.',
 'Absence of negative adjacent timestamps cannot prove no clock movement: S3 interval is ten seconds, and host/container clocks can adjust differently.',
 'Windows event proves host correction; no continuous cross-clock bracket was recorded during the event.']}
(OUT/'probe-clock-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
validation=json.loads((BATCH/'validation.json').read_text())
adjudication={'created_at_utc':evidence['created_at_utc'],'original_collection':'study-002',
 'original_validation_sha256':hashlib.sha256((BATCH/'validation.json').read_bytes()).hexdigest(),
 'status':'quality_veto; replacements not yet run','frozen_criterion':'abs(theft_schedule_error_seconds) <= 1 for non-engineering S3/S4',
 'original_statistics':{k:validation[k] for k in ['planned','completed','retained_infrastructure_failures','raw_valid','raw_files_checked','task_outcomes','provider_error_runs','model_error_runs','tamper_detected','tamper_total','computed_or_ceiling_cost_usd']},
 'invalid_timing_cells':[{k:r.get(k) for k in fields} for r in invalid],
 'prior_infrastructure_failure':[{k:r.get(k) for k in fields+['error']} for r in failed],
 'clock_evidence':{'windows_event_file':'windows-clock-events.json','event_record_id':2808,'host_step_seconds':EVENT-OLD,'scope_count':len(scope),'probing':evidence['probing_at_step'],'sleeping':evidence['sleeping_at_step']},
 'structural_analysis_eligibility_is_sufficient':False,
 'decision':'Retain originals and failed validation unchanged. Four same-cell/same-seed linked infrastructure replacements are warranted for frozen handoff violations, but alone do not clear timing-quality defects/uncertainty in the other 27 event-overlapping probe runs. Eight of those streams have directly observed backward client timestamps.',
 'claim_boundary':'No unqualified full-study support declaration while timing validation fails or event-overlap timing uncertainty is unresolved. Committed outcomes and raw integrity remain reportable with explicit quality flags.',
 'replacement_proposal':['Before new runs, version the outcome-independent exact inclusion/exclusion and timing-specific sensitivity plan; do not change the frozen threshold.',
 'Four maximum-one linked replacements use identical task, condition, lifetime, mode, seed, model and original settings, with fresh isolated state and preserved original records.',
 'Any wider timing replacement must be prespecified for all 27 event-overlapping probe runs rather than selected by security result or significance; a four-only repair must retain an explicit unresolved 27-run timing limitation.',
 'Keep original analysis and separately labeled repaired/sensitivity derivations. Ordinary earliest-terminal deduplication will retain the completed originals; an explicit versioned inclusion overlay is needed, never raw status edits or silent pooling.',
 'New timing instrumentation/clock protections constitute an engineering amendment and must be declared and verified before collection; no retroactive correction of raw timestamps.'],
 'original_mutations':False,'reruns_executed':False}
(OUT/'adjudication.json').write_text(json.dumps(adjudication,indent=2)+'\n')
print(json.dumps({'scope':len(scope),'probing':evidence['probing_at_step'],'sleeping':evidence['sleeping_at_step'],'negative_probe_timestamp_runs':evidence['runs_with_negative_probe_timestamps'],'invalid':len(invalid)}))
