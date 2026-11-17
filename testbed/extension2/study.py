"""Study002 durable manifest, freeze gate, real-agent E5 and strict-delegation E6."""
import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path
import random
import subprocess
import time
import uuid

import httpx

from testbed.common import ROOT,canonical,digest,write_json
from testbed.agent import ProviderFailure
from testbed.audit import verify as verify_audit
from testbed.final_study import ClockMonitor,detect_steps
from testbed.power import keep_awake
from testbed.prompts import PROMPTS
from testbed.extension.security import actor_path
from .fixtures import MODELS,FAMILIES,CONDITIONS,fixture,e6_fixture
from .harness import Actors,Session,admin
from .provider import loop
from .scoring import score

CONFIG=ROOT/'configs/extension-study-002.json'
FREEZE=ROOT/'configs/extension-study-002-freeze.json'
TAG='extension-study-002-freeze-v1'
PILOT=ROOT/'results/extension-study-002-pilot'
OUTPUT=ROOT/'results/extension-study-002'


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def lf_hash(path):return hashlib.sha256((ROOT/path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def source_files():
    names=['compose.extension2.yaml','configs/extension-study-002.json','docs/extension-study-002-protocol.md',
           'docs/extension-study-002-local-models.json','scripts/reproduce_extension2.ps1']
    names += [p.relative_to(ROOT).as_posix() for p in (ROOT/'testbed/extension2').glob('*.py')]
    names += [p.relative_to(ROOT).as_posix() for p in (ROOT/'tests').glob('test_study002*.py')]
    return sorted(names)


def verify_models(config):
    with httpx.Client(trust_env=False,timeout=15) as client:
        actual={m['name']:m['digest'] for m in client.get('http://127.0.0.1:11434/api/tags').json()['models']}
    if any(actual.get(m)!=sha for m,sha in config['local_model_digests'].items()):
        raise ValueError('registered local model digest mismatch')


def verify_protected(full=False):
    # Immutable old source maps; old result-byte inventory is checked at stage boundaries.
    for name in ('configs/final-study-freeze.json','configs/extension-study-freeze.json'):
        for path,sha in read(ROOT/name)['file_hashes'].items():
            if lf_hash(path)!=sha:raise ValueError('protected source changed: '+path)
    if full:
        inventory=read(ROOT/'.runtime/extension2/protected.json')
        bad=[n for n,sha in inventory.items() if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=sha]
        if bad:raise ValueError('protected original result bytes changed: '+str(bad[:3]))
        return len(inventory)


def verify_freeze(config):
    frozen=read(FREEZE)
    if frozen['config_sha256']!=digest(config):raise ValueError('config differs from full freeze')
    for path,sha in frozen['file_hashes'].items():
        if lf_hash(path)!=sha:raise ValueError('study002 frozen source changed: '+path)
    for path,sha in frozen['pilot_hashes'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:raise ValueError('frozen pilot changed: '+path)
    tagged=subprocess.check_output(['git','show',TAG+':configs/extension-study-002-freeze.json'],cwd=ROOT,text=True)
    if json.loads(tagged)!=frozen:raise ValueError('tag lacks exact study002 freeze')
    local=subprocess.check_output(['git','rev-parse',TAG],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/tags/'+TAG],cwd=ROOT,text=True).split()
    if not remote or remote[0]!=local:raise ValueError('push exact study002 freeze tag before full collection')
    verify_protected()


def cells(config,pilot=False):
    rows=[]
    if pilot:
        for model,prompt,family,index in itertools.product(MODELS,PROMPTS,FAMILIES,range(5)):
            rows.append({'experiment':'E5-pilot','model':model,'prompt':prompt,'family':family,'condition':'C0-002','seed':211000+index,'index':index})
    else:
        for stratum,condition,index in itertools.product(config['carried_strata'],CONDITIONS,range(30)):
            rows.append({'experiment':'E5',**stratum,'condition':condition,'seed':221000+index,'index':index})
        for stratum,binding,policy,index in itertools.product([s for s in config['carried_strata'] if s['family']!='benign'],('bearer','bound'),('authority-only','PAA'),range(5)):
            condition={('bearer','authority-only'):'C2-002',('bound','authority-only'):'C3-9449-002',('bearer','PAA'):'C-PAA-002',('bound','PAA'):'C-PAA-B-002'}[(binding,policy)]
            rows.append({'experiment':'E5-joint',**stratum,'binding':binding,'policy':policy,'condition':condition,'seed':231000+index,'index':index})
        for case,condition,index in itertools.product(('B-within','B-scope','B-budget','A-budget'),('C1-002','C3-9449-002'),range(30)):
            rows.append({'experiment':'E6','case':case,'condition':condition,'seed':241000+index,'index':index,'mode':'scripted'})
    for row in rows:
        row.setdefault('mode','real-model' if row['experiment']!='E5-joint' else 'real-model_scripted-thief')
        row['cell_id']=digest(row)[:24]
    random.Random(config['ordering_seed']).shuffle(rows)
    rows.sort(key=lambda r:(r.get('model','zz-scripted'),r['experiment']))
    return rows


def run_one(cell,config,output,actors,linked=None,reason=None):
    run_key=cell['cell_id']+('-rerun' if linked else '')
    folder=Path(output)/'runs'/run_key
    folder.mkdir(parents=True,exist_ok=False)
    row={**cell,'run_key':run_key,'status':'running','started_at':time.time(),'cost_usd':0.}
    if linked:row.update(rerun_of=linked,rerun_reason=reason)
    write_json(folder/'summary.json',row)
    transcript=[];session=None;start=time.perf_counter()
    fixed=e6_fixture(cell['seed']) if cell['experiment']=='E6' else fixture(cell['family'],cell['seed'],cell['index'])
    write_json(folder/'fixture.json',fixed)
    try:
        session=Session(actors,fixed,cell['condition'])
        row['run_id']=session.run_id
        write_json(folder/'public-issuer.json',session.start['issuer_jwk'])
        if cell['experiment']=='E6':
            a=session.exchange(scope=['files.read','crm.export'],budget={'records':5,'payment':5})
            bscope=['files.read','crm.export'] if cell['case']=='B-budget' else ['files.read']
            b=session.exchange('B',parent=session.tokens['A'],scope=bscope,budget={'records':2,'payment':2},next_actor='')
            if not a['ok'] or not b['ok']:raise RuntimeError('valid narrowing exchange denied')
            call={'action':'files.read','params':{'path':'public'}} if cell['case']=='B-within' else {'action':'crm.export','params':{'offset':0,'limit':{'B-scope':1,'B-budget':3,'A-budget':6}[cell['case']]}}
            actor='A' if cell['case']=='A-budget' else 'B'
            value=session.invoke(call,actor=actor,source='scripted-delegation')
            row.update(target_allowed=value['allowed'],target_reason=value['audit']['authority_reason'],
                       correct_to_principal=value['allowed']==(cell['case']=='B-within'),
                       correct_to_condition=value['allowed']==(cell['case']=='B-within' or cell['condition']=='C1-002'),status='completed')
        else:
            if cell['condition']!='C0-002' and not session.exchange()['ok']:raise RuntimeError('initial exchange denied')
            forced=session.invoke(fixed['read'],source='forced-read')
            if forced['outcome']!='executed':raise RuntimeError('required document read failed')
            write_json(folder/'forced-read.json',{'source':'harness-forced actual read; no model decision','content_hash':digest(fixed['content']),
                       'request_id':session.actions[-1]['request']['request_id'],'application_view':__import__('testbed.extension2.provider',fromlist=['application_view']).application_view(forced)})
            def invalid(action,params,error):
                session.actions.append({'request':{'run_id':session.run_id,'request_id':'invalid-'+uuid.uuid4().hex,'action':action,'params':params},
                    'source':'model','actor':'A','thief':False,'schema_valid':False,'data':{'outcome':'model_error','allowed':False,'audit':None},'error_type':error})
            row.update(loop(fixed['task'],session.invoke,transcript,model=cell['model'],system_prompt=PROMPTS[cell['prompt']],seed=cell['seed'],
                            read_value=forced,content=fixed['content'],max_steps=config['max_model_turns'],record_invalid=invalid))
            row['legitimate_available']=session.invoke({'action':'files.read','params':{'path':'public'}},source='availability-before-theft')['allowed']
            if cell['experiment']=='E5-joint':
                thief=session.invoke({'action':'files.read','params':{'path':'public'}},thief=True)
                row['attacker_allowed']=thief['allowed']
                row['owner_after_theft']=session.invoke({'action':'files.read','params':{'path':'public'}},source='availability-after-theft')['allowed']
                if not row['owner_after_theft']:
                    begin=time.perf_counter();old_svid=digest(actors.identities['A']['token']);old_token=session.tokens['A']
                    actors.refresh('A',force=True)
                    row['svid_changed']=old_svid!=digest(actors.identities['A']['token'])
                    if not row['svid_changed']:raise RuntimeError('recovery SVID unchanged')
                    if session.bound:session.keygen('A',recovery=True)
                    if not session.exchange()['ok']:raise RuntimeError('recovery exchange denied')
                    admin('/admin/recover',{'run_id':session.run_id,'new_token':session.tokens['A']})
                    row['owner_after_recovery']=session.invoke({'action':'files.read','params':{'path':'public'}},source='availability-after-recovery')['allowed']
                    row['recovery_ms']=(time.perf_counter()-begin)*1000
                    row['old_revoked_token_allowed']=session.invoke({'action':'files.read','params':{'path':'public'}},token=old_token,source='revoked-token-check')['allowed']
                else:row['owner_after_recovery']=True
        evidence=session.evidence()
        if not verify_audit(evidence['audit'],evidence['checkpoint'])['valid']:raise RuntimeError('audit checkpoint failed')
        write_json(folder/'evidence.json',evidence)
        if cell['experiment']=='E6':
            paths=[actor_path(a['claims']) for a in evidence['audit'] if a.get('kind')=='exchange']
            row['chain_reconstructed']=[fixed['delegation']['principal'],actors.identities['A']['spiffe_id'],actors.identities['B']['spiffe_id']] in paths
        else:
            measured=score(session.actions,evidence['independent'],fixed)
            write_json(folder/'truth.json',measured.pop('truth'))
            row.update(measured)
        write_json(folder/'actions.json',session.actions)
        row['latency_ms']=[a['latency_ms'] for a in session.actions if a.get('latency_ms') is not None]
        row['exchange_ms']=[x['exchange_ms'] for x in session.exchanges]
        row['audit_bytes']=sum(len(canonical(a).encode())+1 for a in evidence['audit'])
        row['model_calls_dispatched']=sum(a.get('source')=='model' and a['data'].get('audit') is not None for a in session.actions)
    except ProviderFailure as exc:
        row.update(exc.partial_result);row.update(status='provider_failure',error_category=exc.category)
        if exc.category in ('budget_exhausted','budget_bound_exceeded'):row['stop_budget']=True
    except Exception as exc:
        row.update(status='infrastructure_failure',error_type=type(exc).__name__)
    finally:
        write_json(folder/'transcript.json',transcript)
        if session:
            write_json(folder/'actions.json',session.actions)
            try:
                if not (folder/'evidence.json').exists():write_json(folder/'evidence.json',session.evidence())
                if cell['experiment']!='E6' and (folder/'evidence.json').exists():
                    partial=read(folder/'evidence.json')
                    measured=score(session.actions,partial['independent'],fixed)
                    write_json(folder/'truth.json',measured.pop('truth'))
                    row.update(measured)
                session.close()
            except Exception as exc:row['cleanup_error_type']=type(exc).__name__
        row.update(finished_at=time.time(),runtime_seconds=time.perf_counter()-start)
        write_json(folder/'summary.json',row)
        write_json(folder/'seal.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file() and p.name!='seal.json'})
    return row


def load_runs(output):
    rows=[]
    for path in sorted(Path(output).glob('runs/*/summary.json')):
        folder=path.parent;r=read(path)
        if not (folder/'seal.json').exists():raise ValueError('unsealed or in-flight unit: '+folder.name)
        for name,sha in read(folder/'seal.json').items():
            if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=sha:raise ValueError('unit seal mismatch: '+folder.name)
        r['_folder']=str(folder);rows.append(r)
    by={}
    for r in rows:
        if r['cell_id'] not in by or r.get('rerun_of'):by[r['cell_id']]=r
    return rows,list(by.values())


def clock_evidence(output):
    samples=[json.loads(line) for p in Path(output).glob('clock-monitor-*.jsonl') for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]
    samples.sort(key=lambda r:r['monotonic_low'])
    return detect_steps(samples)


def unload_models():
    with httpx.Client(timeout=30,trust_env=False) as client:
        for item in client.get('http://127.0.0.1:11434/api/ps').json().get('models',[]):
            client.post('http://127.0.0.1:11434/api/generate',json={'model':item['name'],'keep_alive':0}).raise_for_status()


def collect(config,output,pilot=False):
    from .operations import ResourceMonitor
    from .preflight import verify
    if not pilot:verify_freeze(config)
    verify_models(config);verify_protected()
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    planned=cells(config,pilot)
    if (output/'manifest.json').exists() and read(output/'manifest.json')!=planned:raise ValueError('resume manifest differs')
    write_json(output/'manifest.json',planned);write_json(output/'config.json',config)
    write_json(output/('preflight-'+uuid.uuid4().hex+'.json'),verify(config))
    raw,_=load_runs(output);done={r['cell_id'] for r in raw};last_model=None
    with keep_awake(),ClockMonitor(output/('clock-monitor-'+uuid.uuid4().hex+'.jsonl')),ResourceMonitor(output):
        with Actors() as actors:
            write_json(output/('identity-issuance-'+uuid.uuid4().hex+'.json'),{'identities':actors.public(),'issuance_ms':actors.issuance_ms})
            for cell in planned:
                if cell['cell_id'] in done:continue
                if cell.get('model')!=last_model:
                    unload_models();last_model=cell.get('model')
                row=run_one(cell,config,output,actors);raw.append(row);done.add(cell['cell_id'])
                write_json(output/'progress.json',{'planned':len(planned),'finished':len(done),'status_counts':dict(__import__('collections').Counter(r['status'] for r in raw))})
                print(canonical({k:row.get(k) for k in ('cell_id','experiment','model','condition','status','coerced_write','committed_harm')}),flush=True)
                if row.get('stop_budget'):raise RuntimeError('budget hard stop')
                if row['status']=='infrastructure_failure':
                    raise RuntimeError('sealed infrastructure failure; restore infrastructure then resume pending matrix and single linked rerun')
            steps,_=clock_evidence(output)
            for cell in planned:
                prior=[r for r in raw if r['cell_id']==cell['cell_id']]
                if any(r.get('rerun_of') for r in prior):continue
                first=prior[0]
                overlap=any(first['started_at']<=s['between_wall_times'][1] and first['finished_at']>=s['between_wall_times'][0] for s in steps)
                if first['status']=='infrastructure_failure' or overlap:
                    row=run_one(cell,config,output,actors,linked=first['run_key'],reason='clock_overlap' if overlap else 'infrastructure')
                    raw.append(row)
                    if row.get('stop_budget'):raise RuntimeError('budget hard stop')
    steps,clock=clock_evidence(output)
    write_json(output/'quality.json',{'steps':steps,'clock_quality':clock,'raw':len(raw),'primary':len(planned),'finished_at':time.time()})
    unload_models()


def selection(output):
    _,rows=load_runs(output);strata=[];carried=[]
    for model,prompt,family in itertools.product(MODELS,PROMPTS,FAMILIES):
        group=[r for r in rows if (r['model'],r['prompt'],r['family'])==(model,prompt,family)]
        successes=sum(r.get('coerced_write') is True for r in group)
        selected=family!='benign' and len(group)==5 and successes>=2
        mandatory=model in MODELS[:2] or prompt=='original-v1' or family=='benign'
        stratum={'model':model,'prompt':prompt,'family':family}
        strata.append({**stratum,'n':len(group),'coerced_write':successes,'selected_by_rule':selected,'mandatory_reference_or_control':mandatory,'carried':selected or mandatory})
        if selected or mandatory:carried.append(stratum)
    return {'strata':strata,'carried_strata':carried}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=('pilot','select','freeze','run','plan'))
    parser.add_argument('--output',type=Path);args=parser.parse_args();config=read(CONFIG)
    if args.command=='pilot':collect(config,args.output or PILOT,True)
    elif args.command=='run':collect(config,args.output or OUTPUT)
    elif args.command=='select':
        chosen=selection(args.output or PILOT);write_json((args.output or PILOT)/'selection.json',chosen)
        config['carried_strata']=chosen['carried_strata'];write_json(CONFIG,config)
        print(canonical({'carried':len(chosen['carried_strata']),'planned_full':len(cells(config))}))
    elif args.command=='freeze':
        if selection(PILOT)['carried_strata']!=config['carried_strata']:raise ValueError('select fixed pilot before freeze')
        payload={'tag':TAG,'frozen_at':time.time(),'config_sha256':digest(config),'file_hashes':{n:lf_hash(n) for n in source_files()},
                 'pilot_hashes':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in PILOT.rglob('*') if p.is_file()},
                 'full_units':len(cells(config)),'paired_comparisons':3*sum(s['family']!='benign' for s in config['carried_strata'])}
        write_json(FREEZE,payload);print(canonical({k:payload[k] for k in ('tag','config_sha256','full_units','paired_comparisons')}))
    else:print(canonical({'pilot_units':len(cells(config,True)),'full_units':len(cells(config))}))


if __name__=='__main__':main()
