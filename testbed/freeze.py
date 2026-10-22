"""Pre-run freeze: refuse approval without preserved measured real-LLM pilot evidence."""
import argparse
import json
import subprocess
import time
from pathlib import Path
from .common import ROOT,digest,write_json
from .runner import manifest,config_fingerprint

def approve(pilot,study):
    pilot=Path(pilot).resolve();study=Path(study).resolve()
    config=json.loads(study.read_text(encoding='utf-8-sig'))
    if config['phase']!='full' or config['mode']!='llm' or config['repeats']<30: raise ValueError('Invalid full-study design')
    if set(config['conditions'])!={'C0','C1','C2','C2-noWF','C2-RS'} or set(config['scenarios'])!={'S1','S2','S3','S4','S5'}:
        raise ValueError('Incomplete study matrix')
    if set(config['ttl_seconds'])!={300,900,3600} or set(config['revocation_modes'])!={'now','expiry'}: raise ValueError('Incomplete timing sweep')
    from analysis.cli import verify_raw
    verification=verify_raw(pilot)
    if not verification['valid']:raise ValueError('Pilot raw evidence failed seal verification')
    pilot_config=json.loads((pilot/'config.json').read_text(encoding='utf-8'))
    pilot_manifest=json.loads((pilot/'manifest.json').read_text(encoding='utf-8'))
    batch_status=json.loads((pilot/'batch-status.json').read_text(encoding='utf-8'))
    if batch_status['remaining_failures']:raise ValueError('Pilot has unresolved infrastructure failures')
    if pilot_config.get('theft_delay_seconds')!=config.get('theft_delay_seconds') or pilot_config.get('concurrency')!=config.get('concurrency'):
        raise ValueError('Final pilot must validate the frozen handoff timing and concurrency')
    rows=[json.loads(p.read_text()) for p in pilot.glob('runs/*/summary.json')]
    successful=[x for x in rows if x['status']=='completed' and x['mode']=='llm' and x['phase']=='pilot']
    if not successful: raise ValueError('No measured real-LLM pilot')
    expected={(c,s) for c in config['conditions'] for s in config['scenarios'] if c not in ['C2-noWF','C2-RS'] or s in ['S2','S5']}
    if not expected<={(r['condition'],r['scenario']) for r in successful}: raise ValueError('Pilot does not cover every required condition/scenario')
    if any(sum((r['condition'],r['scenario'])==cell for r in successful)<3 for cell in expected): raise ValueError('Pilot requires at least three repeated runs per main/ablation cell')
    if any(r['metadata'].get('model')!=config['model'] or not r.get('usage') or not r.get('cost_usd',0)>0 for r in successful):
        raise ValueError('Pilot model/usage/cost evidence missing or differs')
    if any(not (pilot/'runs'/r['run_id']/'transcript.json').is_file() for r in successful): raise ValueError('Transcript missing')
    if any(r.get('audit_total',0)==0 or not r.get('latencies_ms') or r.get('attribution_true') is None for r in successful):
        raise ValueError('Pilot measurement coverage incomplete')
    planned=manifest(pilot_config)
    fields=['condition','scenario','ttl_seconds','revocation_mode','seed','pair_id']
    key=lambda row:tuple(row[k] for k in fields)
    if {key(r) for r in successful}!={key(r) for r in planned}:raise ValueError('Pilot terminal cells do not cover the full planned matrix')
    if any(r.get('tamper_detected')!=r.get('tamper_total') or r.get('tamper_total')!=5 for r in successful):raise ValueError('Pilot tamper sanity checks incomplete')
    for row in successful:
        folder=pilot/'runs'/row['run_id']
        if not (folder/'tool-ground-truth.json').is_file():raise ValueError('Independent tool-state oracle missing')
        if row['scenario'] in ['S3','S4']:
            if abs(row.get('theft_schedule_error_seconds',float('inf')))>1:raise ValueError('Pilot theft handoff schedule invalid')
            if row['scenario']=='S4' and row['revocation_mode']=='now' and not row.get('event_observed'):raise ValueError('Pilot immediate revocation lacks observed denial')
            if row['condition']!='C0' and not row.get('event_observed'):raise ValueError('Pilot credential expiration lacks observed denial')
    from scripts.verify_pilot_source import verify as verify_pilot_source
    runtime_match=verify_pilot_source(pilot)
    if not runtime_match['passed']:raise ValueError('Experiment runtime differs from validated pilot bytes')
    mean=sum(r['cost_usd'] for r in successful)/len(successful)
    projected=mean*len(manifest(config))*1.5
    from .agent import Budget
    from contextlib import closing
    import sqlite3
    budget=Budget(config.get('budget_usd',0))
    with closing(sqlite3.connect(budget.path)) as ledger:
        already_used=ledger.execute('SELECT coalesce(sum(coalesce(actual,reserved)),0) FROM spend').fetchone()[0]
    if budget.limit-already_used<projected:raise ValueError('Remaining aggregate budget does not cover projected cost plus50percent reserve')
    # Freeze only committed reviewable code. Do not silently bless a dirty working tree.
    dirty=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
    if dirty.strip(): raise ValueError('Commit/push source and pilot evidence before freeze; working tree must be clean')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],cwd=ROOT,text=True).split()
    if not remote or remote[0]!=head:raise ValueError('Push the reviewed commit before approving freeze')
    files={}
    for directory in ['testbed','infra','analysis','configs']:
        for path in (ROOT/directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.name!='freeze.json':
                files[str(path.relative_to(ROOT)).replace('\\','/')]=digest(path.read_text(encoding='utf-8'))
    for name in ['scripts/spire.py','scripts/tool_evidence.py','compose.yaml','Dockerfile','requirements.txt','requirements.lock.txt']:
        files[name]=digest((ROOT/name).read_text(encoding='utf-8'))
    freeze={'status':'approved' ,'tag':'study-freeze-v1','approved_at':time.time(),'repeats':config['repeats'],'pilot':str(pilot.relative_to(ROOT)),
      'pilot_runtime_byte_match_files':runtime_match['matched_file_count'],'aggregate_spend_before_full_usd':already_used,'remaining_aggregate_budget_usd':budget.limit-already_used,'pilot_runs':len(successful),'pilot_manifest_sha256':digest(pilot_manifest),'pilot_raw_verified_files':verification['files_checked'],'pilot_mean_cost_usd':mean,'projected_study_cost_usd_with_reserve':projected,
      'study_config_sha256':config_fingerprint(config),'file_hashes':files,
      'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      'analysis_plan_sha256':digest((ROOT/'docs/analysis-plan.md').read_text(encoding='utf-8')),
      'sample_size_reason':'30default; Wilson zero-failure upper bound remains about11.4percent; no optional outcome-based additions',
      'note':'Commit this freeze, push and tag before launching full runs. Fixed prompts/payloads/policies/config hashes enforce changes fail closed.'}
    write_json(ROOT/'configs/freeze.json',freeze)
    return freeze

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--pilot',required=True);parser.add_argument('--study',default='configs/study.json')
    args=parser.parse_args();print(json.dumps(approve(args.pilot,args.study),indent=2))

if __name__=='__main__':main()
