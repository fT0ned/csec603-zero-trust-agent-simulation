"""Read-only collection validation, preserving failures and raw evidence."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import time
from analysis.cli import verify_raw
from testbed.runner import manifest

FIELDS=('condition','scenario','ttl_seconds','revocation_mode','seed','pair_id')
def validate(root):
    root=Path(root).resolve()
    config=json.loads((root/'config.json').read_text(encoding='utf-8'))
    planned=manifest(config)
    records=[json.loads(p.read_text(encoding='utf-8')) for p in root.glob('runs/*/summary.json')]
    key=lambda r:tuple(r[x] for x in FIELDS)
    expected=Counter(key(r) for r in planned)
    terminal=[r for r in records if r['status']=='completed']
    observed=Counter(key(r) for r in terminal)
    errors=[];warnings=[]
    if observed!=expected:errors.append('Terminal completed cells differ from planned matrix (missing/duplicate cells).')
    seals=verify_raw(root)
    if not seals['valid']:errors.append('Raw seal verification failed.')
    for row in terminal:
        name=row['run_id'];folder=root/'runs'/name
        for required in ['tool-ground-truth.json','transcript.json','fixture.json','checkpoint.json','tamper.json']:
            if not (folder/required).is_file():errors.append(name+': missing '+required)
        if row.get('tamper_total')!=5 or row.get('tamper_detected')!=5:errors.append(name+': tamper sanity check failed')
        if row.get('mode')=='llm':
            if not row.get('usage') or not row.get('model_snapshots'):errors.append(name+': actual provider usage/model absent')
            if row.get('metadata',{}).get('model')!=config.get('model'):errors.append(name+': requested model mismatch')
            if row.get('cost_usd',0)<=0:warnings.append(name+': no computed positive token cost; inspect retained provider error')
            if row.get('model_errors') or row.get('provider_error'):warnings.append(name+': provider/model failure retained as unit')
        if row['scenario'] in ['S3','S4'] and config['phase']!='engineering':
            if abs(row.get('theft_schedule_error_seconds',float('inf')))>1:errors.append(name+': credential handoff schedule error >1second')
            if row['condition']!='C0' and not row.get('event_observed'):errors.append(name+': expected credential denial not observed')
            if row['scenario']=='S4' and row['revocation_mode']=='now' and not row.get('event_observed'):errors.append(name+': immediate revocation not observed')
        if row['condition'].startswith('C2') and row.get('audit_complete')!=row.get('audit_total'):errors.append(name+': C2 full audit coverage incomplete')
        evidence_path=folder/'tool-ground-truth.json'
        if evidence_path.is_file():
            evidence=json.loads(evidence_path.read_text(encoding='utf-8'))
            if row['scenario']=='S5':
                ratio=(len(evidence['crm']['state']['exports'])/10 if row['payload_id']=='chunked-export'
                       else sum(x['amount'] for x in evidence['payments']['state']['payments'])/100)
                if abs(ratio-row['cumulative_ratio'])>1e-9:errors.append(name+': cumulative ratio differs from committed tool-state oracle')
    timing=[r['theft_schedule_error_seconds'] for r in terminal if 'theft_schedule_error_seconds' in r and config['phase']!='engineering']
    result={'created_at':time.time(),'collection':root.name,'phase':config['phase'],'mode':config['mode'],
      'planned':len(planned),'completed':len(terminal),'retained_infrastructure_failures':sum(r['status']=='infrastructure_failure' for r in records),
      'raw_valid':seals['valid'],'raw_files_checked':seals['files_checked'],'raw_warnings':seals['warnings'],
      'task_outcomes':dict(Counter(r.get('task_outcome') for r in terminal)),
      'provider_error_runs':sum(bool(r.get('provider_error')) for r in terminal),'model_error_runs':sum(bool(r.get('model_errors')) for r in terminal),
      'computed_or_ceiling_cost_usd':sum(r.get('cost_usd',0) for r in terminal),
      'uncertain_reservations_usd':sum(r.get('uncertain_reservations_usd',0) for r in terminal),
      'max_absolute_theft_schedule_error_seconds':max(map(abs,timing)) if timing else None,
      'tamper_detected':sum(r.get('tamper_detected',0) for r in terminal),'tamper_total':sum(r.get('tamper_total',0) for r in terminal),
      'errors':errors,'warnings':warnings,'passed':not errors,
      'scope':'Read-only consistency validation; successful sanity checks do not establish research hypotheses. Token cost may include labeled price ceilings; provider balance reconciliation is separate.'}
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',required=True,type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=validate(args.input)
    destination=args.output or args.input/'validation.json';destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['collection','planned','completed','raw_valid','errors','warnings','passed']}))
    return 0 if result['passed'] else 2

if __name__=='__main__':raise SystemExit(main())
