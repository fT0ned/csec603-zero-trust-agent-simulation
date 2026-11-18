"""Post-collection preservation and accounting; never modifies frozen evidence."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import sqlite3
import subprocess
import time

from testbed.common import ROOT, write_json
from testbed.extension2.study import read, load_runs, verify_freeze, verify_protected, clock_evidence
from testbed.final_study import detect_steps


def main():
    config=read(ROOT/'configs/extension-study-002.json')
    verify_freeze(config)
    protected=verify_protected(full=True)
    inventory=read(ROOT/'.runtime/extension2/protected.json');trees={}
    for prefix in ('results/final-study-001','results/extension-study-001'):
        actual={p.relative_to(ROOT).as_posix() for p in (ROOT/prefix).rglob('*') if p.is_file()}
        expected={name for name in inventory if name.startswith(prefix+'/')}
        if actual!=expected:raise ValueError('Protected result file set changed: '+prefix)
        before=subprocess.check_output(['git','rev-parse','b61960cc0:'+prefix],cwd=ROOT,text=True).strip()
        after=subprocess.check_output(['git','rev-parse','HEAD:'+prefix],cwd=ROOT,text=True).strip()
        if before!=after:raise ValueError('Protected Git tree differs: '+prefix)
        trees[prefix]={'baseline_commit':'b61960cc0','baseline_tree':before,'current_tree':after,'filesystem_files':len(actual),'unchanged':True}
    ledger=ROOT/'.runtime/spend.sqlite'
    baseline=read(ROOT/'docs/extension-study-002-budget-baseline.json')
    # Open read-only: reservation IDs, not credentials or prompts, are exported.
    with sqlite3.connect(ledger.as_uri()+'?mode=ro',uri=True) as db:
        columns=[r[1] for r in db.execute('PRAGMA table_info(spend)')]
        current=[dict(zip(columns,row)) for row in db.execute('SELECT * FROM spend ORDER BY id')]
    earlier=[r for r in current if r['id']<=baseline['last_id']]
    later=[r for r in current if r['id']>baseline['last_id']]
    charged=lambda rows:sum(r['actual'] if r['actual'] is not None else r['reserved'] for r in rows)
    if abs(charged(earlier)-baseline['conservative_usd'])>1e-8:
        raise ValueError('Historical spending ledger changed')
    known={}; phases={}; duplicate_ids=[]
    for name in ('extension-study-002-pilot','extension-study-002'):
        folder=ROOT/'results'/name
        raw,primary=load_runs(folder)
        planned=read(folder/'manifest.json')
        if {r['cell_id'] for r in primary}!={r['cell_id'] for r in planned}:
            raise ValueError('Missing or extra primary units: '+name)
        phase_config=read(folder/'config.json')
        pins={**phase_config['local_model_digests'],**phase_config.get('profile_model_digests',{})}
        ids=[]; total=0.; returned=set(); contexts=[]; failures=[]; http429=0
        context_checks=[]
        for row in raw:
            transcript=read(Path(row['_folder'])/'transcript.json')
            for call in transcript:
                http429+=call.get('http_status')==429
                rid=call.get('reservation_id')
                if rid is not None:
                    if rid in known:duplicate_ids.append(rid)
                    known[rid]=name;ids.append(rid)
                total+=call.get('cost_usd') or 0
                if 'response' in call:returned.add(call['response'].get('model','unreported'))
            contexts.extend(row.get('local_context_observations',[]))
            if row.get('model') in phase_config['local_model_digests'] and row.get('exposure') is True:
                wire=phase_config.get('runtime_model_profiles',{}).get(row['model'],row['model'])
                observed=[v for v in row.get('local_context_observations',[]) if v.get('name')==wire]
                context_checks.append({'cell_id':row['cell_id'],'observed':bool(observed),
                    'matches':bool(observed) and all(v.get('digest')==pins[wire] and v.get('context_length')==phase_config['context_local'] for v in observed)})
            if row['status'] not in ('completed','model_step_limit'):
                failures.append({'cell_id':row['cell_id'],'status':row['status'],'rerun_of':row.get('rerun_of')})
        matched=[r for r in later if r['id'] in ids]
        steps,clock=clock_evidence(folder)
        monitor_periods=[]
        for path in sorted(folder.glob('clock-monitor-*.jsonl')):
            samples=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
            period_steps,period_quality=detect_steps(samples)
            monitor_periods.append({'file':path.name,'steps':period_steps,'quality':period_quality,
                'first_wall_time':samples[0]['wall_time'] if samples else None,
                'last_wall_time':samples[-1]['wall_time'] if samples else None})
        phases[name]={'planned':len(planned),'raw':len(raw),'primary':len(primary),
            'reservations':len(ids),'transcript_cost_usd':total,'ledger_charged_usd':charged(matched),
            'uncertain_usd':sum(r['reserved'] for r in matched if r['actual'] is None),
            'returned_model_ids':sorted(returned),'http429_events':http429,
            'first_started_at':min(r['started_at'] for r in raw),'last_finished_at':max(r['finished_at'] for r in raw),
            'collection_span_seconds':max(r['finished_at'] for r in raw)-min(r['started_at'] for r in raw),
            'sum_raw_run_seconds':sum(r['runtime_seconds'] for r in raw),
            'clock_steps':steps,'clock_quality':clock,'monitor_periods':monitor_periods,
            'failures':failures,
            'runtime_context_counts':[{'observation':json.loads(key),'count':count} for key,count in sorted(Counter(json.dumps(v,sort_keys=True) for v in contexts).items())],
            'local_units_requiring_runtime_observation':len(context_checks),
            'local_units_digest_and_context_verified':sum(v['matches'] for v in context_checks),
            'local_units_runtime_observation_missing':[v['cell_id'] for v in context_checks if not v['observed']],
            'local_units_runtime_digest_or_context_discrepancies':[v['cell_id'] for v in context_checks if v['observed'] and not v['matches']]}
    if duplicate_ids:raise ValueError('Reservation appears twice: '+str(duplicate_ids[:3]))
    unmatched=[r for r in later if r['id'] not in known]
    if charged(current)>25+1e-9:raise ValueError('Budget cap exceeded')
    output={'checked_at':time.time(),'protected_paths_unchanged':protected,'protected_result_trees':trees,
        'freeze_tag':'extension-study-002-freeze-v1',
        'freeze_commit':subprocess.check_output(['git','rev-list','-n','1','extension-study-002-freeze-v1'],cwd=ROOT,text=True).strip(),
        'freeze_file_sha256':hashlib.sha256((ROOT/'configs/extension-study-002-freeze.json').read_bytes()).hexdigest(),
        'config_sha256':read(ROOT/'configs/extension-study-002-freeze.json')['config_sha256'],
        'baseline':baseline,'global_ledger_charged_usd':charged(current),
        'study002_ledger_charged_usd':charged(later),'unattributed_reservations':unmatched,
        'unattributed_charged_usd':charged(unmatched),'phases':phases}
    write_json(ROOT/'docs/extension-study-002-closeout.json',output)
    write_json(ROOT/'docs/extension-study-002-spending-ledger.json',{'baseline':baseline,'entries':later})
    print(json.dumps({k:output[k] for k in ('protected_paths_unchanged','global_ledger_charged_usd','study002_ledger_charged_usd','unattributed_charged_usd')}))


if __name__=='__main__':main()
