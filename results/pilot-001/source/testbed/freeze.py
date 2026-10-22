"""Pre-run freeze: refuse approval without preserved measured real-LLM pilot evidence."""
import argparse
import json
import subprocess
import time
from pathlib import Path
from .common import ROOT,digest,write_json
from .runner import manifest

def approve(pilot,study):
    pilot=Path(pilot).resolve();study=Path(study).resolve()
    config=json.loads(study.read_text(encoding='utf-8-sig'))
    if config['phase']!='full' or config['mode']!='llm' or config['repeats']<30: raise ValueError('Invalid full-study design')
    if set(config['conditions'])!={'C0','C1','C2','C2-noWF','C2-RS'} or set(config['scenarios'])!={'S1','S2','S3','S4','S5'}:
        raise ValueError('Incomplete study matrix')
    if set(config['ttl_seconds'])!={300,900,3600} or set(config['revocation_modes'])!={'now','expiry'}: raise ValueError('Incomplete timing sweep')
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
    mean=sum(r['cost_usd'] for r in successful)/len(successful)
    projected=mean*len(manifest(config))*1.5
    if config.get('budget_usd',0)<projected: raise ValueError('Batch budget does not cover pilot projected cost plus50percent reserve')
    # Freeze only committed reviewable code. Do not silently bless a dirty working tree.
    dirty=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
    if dirty.strip(): raise ValueError('Commit/push source and pilot evidence before freeze; working tree must be clean')
    files={}
    for directory in ['testbed','infra','analysis','configs']:
        for path in (ROOT/directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.name!='freeze.json':
                files[str(path.relative_to(ROOT)).replace('\\','/')]=digest(path.read_text(encoding='utf-8'))
    freeze={'status':'approved','tag':'study-freeze-v1','approved_at':time.time(),'repeats':config['repeats'],'pilot':str(pilot.relative_to(ROOT)),
      'pilot_runs':len(successful),'pilot_mean_cost_usd':mean,'projected_study_cost_usd_with_reserve':projected,
      'study_config_sha256':digest(config),'file_hashes':files,
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
