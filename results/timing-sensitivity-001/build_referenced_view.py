"""Build a transient zero-copy amended view only after explicit repair review.

No default action. --build needs accepted repair-review.json bound to quality and
protocol hashes. Raw bytes are never copied, modified or removed. --analyze is
optional and invokes the unchanged analyzer from the frozen worktree.
"""
import argparse,csv,hashlib,json,os,re,shutil,subprocess,sys,time
from datetime import datetime
from pathlib import Path
OUT=Path(__file__).resolve().parent
MAIN=OUT.parents[1]
VIEW=MAIN/'.runtime/timing-sensitivity-001-view'
FROZEN=MAIN.parent/'GithubRepoFrozenTimingV2'
FIELDS=['condition','scenario','ttl_seconds','revocation_mode','seed','pair_id']
PROSPECTIVE_TAG='timing-endpoint-repair-v1'
PROSPECTIVE_COMMIT='c31ef598f8d3492500916dda2a2edf0aa623b07f'
REVIEW_INPUTS=['results/timing-repair-001/quality.json','results/timing-repair-001/quality-adjudication.json',
 'results/quality-study002/quality-adjudication.json','results/quality-study002/probe-clock-evidence.json',
 'results/timing-repair-001/repair-protocol.json','results/timing-repair-002/repair-protocol.json',
 'results/timing-repair-001/replacement-links.jsonl','results/timing-repair-002/replacement-links.jsonl',
 'results/timing-repair-002/quality.json','results/timing-repair-002/endpoint-review.json',
 'results/timing-repair-001/preflight.json','results/timing-repair-002/preflight.json',
 'results/timing-repair-001/started.json','results/timing-repair-002/started.json',
 'results/timing-repair-002/metadata-clarification.json','docs/timing-endpoint-repair-protocol.md']
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def key(r):return tuple(r[k] for k in FIELDS)

def verify_control_snapshot(original,snapshot,deployed_byte_sha256,tagged_snapshot_byte_sha256):
    """Honor the predeclared deployed-CRLF versus Git-LF repair contract.

    Hash each preserved byte representation independently, then compare decoded
    UTF-8 text with universal newline handling. Never rewrite either source.
    """
    if sha(original)!=deployed_byte_sha256:raise ValueError('Original captured deployed control bytes changed')
    if sha(snapshot)!=tagged_snapshot_byte_sha256:raise ValueError('Repair source bytes differ from tagged source manifest')
    if original.read_text(encoding='utf-8')!=snapshot.read_text(encoding='utf-8'):
        raise ValueError('Repair control source text differs beyond declared newline representation')

def verify_predata():
    commit=subprocess.check_output(['git','rev-parse',PROSPECTIVE_TAG+'^{}'],cwd=MAIN,text=True).strip()
    if commit!=PROSPECTIVE_COMMIT:raise ValueError('Prospective tag identity changed')
    paths=['results/timing-sensitivity-001/selection-plan.json']
    for cohort in ['timing-repair-001','timing-repair-002']:
        paths.extend('results/'+cohort+'/'+name for name in ['repair-protocol.json','config.json','manifest.json','collect_repair.py'])
    paths.append('results/timing-repair-002/adjudicate_endpoints.py')
    for name in paths:
        frozen=subprocess.check_output(['git','show',PROSPECTIVE_TAG+':'+name],cwd=MAIN)
        if frozen!=(MAIN/name).read_bytes():raise ValueError('Predata bytes changed: '+name)
    historical_doc=subprocess.check_output(['git','show',PROSPECTIVE_TAG+':docs/timing-endpoint-repair-protocol.md'],cwd=MAIN)
    return {'tag':PROSPECTIVE_TAG,'commit':commit,'tagged_files':{name:sha(MAIN/name) for name in paths},
            'historical_protocol_document_sha256':hashlib.sha256(historical_doc).hexdigest()}

def verify_unit_review(review,rows):
    expected={r['source_run_id']:{k:r[k] for k in ['source_collection','source_run_id','original_run_id','summary_sha256','raw_manifest_sha256']} for r in rows if r['is_replacement']}
    supplied=review.get('selected_replacement_units',[])
    supplied_map={r['source_run_id']:r for r in supplied}
    if len(supplied_map)!=len(supplied) or supplied_map!=expected:raise ValueError('Review must bind exactly every selected replacement summary/raw manifest')
    reviewed_at=datetime.fromisoformat(review['reviewed_at'].replace('Z','+00:00'))
    if reviewed_at.tzinfo is None:raise ValueError('Lead review time must include an explicit timezone')
    reviewed=reviewed_at.timestamp()
    if reviewed<max(read(MAIN/r['source_folder']/'summary.json')['metadata']['finished_at'] for r in rows if r['is_replacement']):
        raise ValueError('Acceptance predates completion of selected replacements')

def selection(require_review=True):
    predata=verify_predata()
    plan=read(OUT/'selection-plan.json');review=read(OUT/'repair-review.json') if require_review else {}
    if require_review and (review.get('status')!='accepted' or review.get('selection_plan_sha256')!=sha(OUT/'selection-plan.json')):
        raise ValueError('Require accepted review bound to predeclared selection plan')
    if require_review and (review.get('builder_sha256')!=sha(Path(__file__)) or review.get('predata')!=predata):raise ValueError('Review builder/predata binding changed')
    if require_review and set(review.get('reviewed_file_sha256',{}))!=set(REVIEW_INPUTS):raise ValueError('Review must bind all applicable assessments/protocols/links/metadata clarification')
    for name in REVIEW_INPUTS:
        actual=sha(MAIN/name)
        if require_review and review['reviewed_file_sha256'][name]!=actual:raise ValueError('Reviewed quality bytes changed')
    if not read(MAIN/'results/timing-repair-001/quality.json').get('passed') or not read(MAIN/'results/timing-repair-002/quality.json').get('passed'):
        raise ValueError('Both repair clock/raw gates must pass; repair002 also includes endpoint gate')
    endpoint002=read(MAIN/'results/timing-repair-002/endpoint-review.json')
    if len(endpoint002.get('runs',[]))!=2 or any(r.get('issues') for r in endpoint002['runs']):raise ValueError('Repair002 endpoint gate incomplete or failed')
    for cohort in ['timing-repair-001','timing-repair-002']:
        if read(MAIN/'results'/cohort/'config.json')!=read(MAIN/'results/study-002/config.json'):raise ValueError('Replacement frozen configuration differs')
        protocol=read(MAIN/'results'/cohort/'repair-protocol.json')
        source_hashes=read(MAIN/'results'/cohort/'manifest.json')['source_sha256']
        for name,expected in protocol['deployed_source_contract']['captured_byte_sha256'].items():
            snapshot_sha=source_hashes.get(name,source_hashes.get(name.replace('/', '\\')))
            if not snapshot_sha:raise ValueError('Tagged repair source manifest missing control: '+name)
            verify_control_snapshot(MAIN/'results/study-002/source'/name,
                MAIN/'results'/cohort/'source'/name,expected,snapshot_sha)
    original_review=read(MAIN/'results/quality-study002/quality-adjudication.json');repair_review=read(MAIN/'results/timing-repair-001/quality-adjudication.json')
    if not original_review.get('audit_complete') or not repair_review.get('audit_complete'):raise ValueError('Endpoint audits incomplete')
    if original_review.get('completed_S3_S4_audited')!=810 or repair_review.get('completed_S3_S4_audited')!=31:raise ValueError('Endpoint audit coverage differs from full original/repair scopes')
    bad_original={x['run_id'] for x in original_review['affected_runs']}
    bad_repair={x['run_id'] for x in repair_review['affected_runs']}
    clocks={x['run_id'] for x in read(MAIN/'results/quality-study002/probe-clock-evidence.json')['runs']}
    declared={x['original_run_id']:x for x in plan['links']}
    if len(declared)!=len(plan['links']) or set(declared)!=clocks|bad_original:
        raise ValueError('Selection differs from full clock scope plus all original semantic failures')
    originals={};base=MAIN/'results/study-002';manifest=read(base/'manifest.json')
    for path in base.glob('runs/*/summary.json'):
        row=read(path)
        if row['status']=='completed':
            if key(row) in originals:raise ValueError('Duplicate original completed cell')
            originals[key(row)]=(path,row)
    if len(originals)!=1200:raise ValueError('Original matrix incomplete')
    if len(manifest['cells'])!=1200 or len({key(cell) for cell in manifest['cells']})!=1200 or {key(cell) for cell in manifest['cells']}!=set(originals):
        raise ValueError('Original manifest is not the exact unique completed matrix')
    candidates={}
    for name in ['timing-repair-001','timing-repair-002']:
        links=[__import__('json').loads(x) for x in (MAIN/'results'/name/'replacement-links.jsonl').read_text().splitlines()]
        by_original={x['original_run_id']:x for x in links}
        if len(by_original)!=len(links):raise ValueError('Multiple attempts per cohort cell')
        candidates[name]=by_original
    rows=[]
    for cell in manifest['cells']:
        path,row=originals[key(cell)];original_id=row['run_id'];choice=declared.get(original_id)
        source='study-002'
        if choice:
            if key(choice)!=key(cell):raise ValueError('Predeclared link cell does not match original')
            source=choice['replacement_collection'];link=candidates[source][original_id]
            if link['status']!='completed' or key(link['cell'])!=key(cell) or link.get('attempt')!=1:raise ValueError('Replacement mismatch or extra attempt')
            if sha(path)!=link['original_summary_sha256']:raise ValueError('Original source changed')
            original_row=row;original_folder=path.parent
            path=MAIN/'results'/source/'runs'/link['replacement_run_id']/'summary.json';row=read(path)
            if row['run_id']!=link['replacement_run_id']:raise ValueError('Replacement summary identity differs from link')
            for field in ['mode','phase']:
                if row.get(field)!=original_row.get(field):raise ValueError('Replacement mode/phase changed')
            for field in ['model','model_snapshot','fixture_sha256','approval_dependent']:
                if row['metadata'].get(field)!=original_row['metadata'].get(field):raise ValueError('Replacement comparability changed: '+field)
            for name in ['fixture.json']:
                if sha(path.parent/name)!=sha(original_folder/name):raise ValueError('Replacement fixture bytes changed')
            first=lambda folder:read(folder/'transcript.json')[0]['request']
            old_request,new_request=first(original_folder),first(path.parent)
            for field in ['model','messages','tools','temperature','max_tokens','thinking','parallel_tool_calls','store']:
                if old_request.get(field)!=new_request.get(field):raise ValueError('Replacement actual initial prompt/settings/tool schema changed: '+field)
        if row['status']!='completed' or key(row)!=key(cell):raise ValueError('Selected cell mismatch')
        if source=='study-002' and original_id in bad_original|clocks:raise ValueError('Invalid original selected')
        if source=='timing-repair-001' and row['run_id'] in bad_repair:raise ValueError('Invalid repair endpoint selected')
        folder=path.parent.resolve()
        if not re.fullmatch(r'r[0-9a-f]{32}',row['run_id']) or not folder.is_relative_to((MAIN/'results'/source/'runs').resolve()):raise ValueError('Unsafe source path')
        rows.append({**cell,'source_collection':source,'source_run_id':row['run_id'],'source_folder':folder.relative_to(MAIN).as_posix(),
            'summary_sha256':sha(path),'raw_manifest_sha256':sha(folder/'raw-manifest.json'),'original_run_id':original_id,'is_replacement':bool(choice)})
    counts={name:sum(x['source_collection']==name for x in rows) for name in ['study-002','timing-repair-001','timing-repair-002']}
    if counts!={'study-002':1168,'timing-repair-001':30,'timing-repair-002':2} or len(rows)!=1200:raise ValueError('Wrong declared source counts')
    if len({row['source_run_id'] for row in rows})!=1200:raise ValueError('Selected run IDs are not unique')
    if {r['source_run_id'] for r in rows if r['source_collection']=='timing-repair-002'}!={r['run_id'] for r in endpoint002['runs']}:
        raise ValueError('Repair002 endpoint review does not cover exactly selected replacement IDs')
    if require_review:
        verify_unit_review(review,rows)
        raw=OUT/'selected-raw-review.json'
        if review.get('selected_raw_verification_sha256')!=sha(raw) or not read(raw).get('valid') or read(raw).get('selected_units')!=rows:
            raise ValueError('Require exact selected-unit preacceptance raw verification')
    return rows,manifest

def verify_selected_raw(rows):
    errors=[];checked=0
    for row in rows:
        folder=(MAIN/row['source_folder']).resolve();manifest=read(folder/'raw-manifest.json')
        if manifest.get('hash_scheme')!='sha256-bytes':raise ValueError('Selected raw verification requires byte manifests')
        for relative,expected in manifest['files'].items():
            path=(folder/relative).resolve()
            if not path.is_relative_to(folder) or path==folder/'raw-manifest.json':raise ValueError('Unsafe raw manifest member')
            checked+=1
            if not path.is_file() or sha(path)!=expected:errors.append({'run_id':row['source_run_id'],'file':relative})
    return {'valid':not errors,'selected_units':rows,'runs':len(rows),'files_checked':checked,'errors':errors}

def prepare_review():
    # Deliberately cannot run while002 quality/endpoint records are incomplete.
    # A draft never authorizes selection or an accepted analysis view.
    if (OUT/'repair-review.json').exists():raise ValueError('Existing lead review must not be overwritten')
    rows,_=selection(False)
    raw=verify_selected_raw(rows);write(OUT/'selected-raw-review.json',raw)
    if not raw['valid']:raise ValueError('Selected raw verification failed; no review draft written')
    selected=[{k:r[k] for k in ['source_collection','source_run_id','original_run_id','summary_sha256','raw_manifest_sha256']} for r in rows if r['is_replacement']]
    fingerprints=[]
    for row in rows:
        if not row['is_replacement']:continue
        before=read(MAIN/'results/study-002/runs'/row['original_run_id']/'summary.json')
        after=read(MAIN/row['source_folder']/'summary.json')
        old=sorted(set(str(x) for x in before.get('system_fingerprints',[])))
        new=sorted(set(str(x) for x in after.get('system_fingerprints',[])))
        fingerprints.append({'original_run_id':row['original_run_id'],'source_run_id':row['source_run_id'],
            'original_fingerprints':old,'replacement_fingerprints':new,'fingerprints_changed':old!=new,
            'actual_model':after['metadata'].get('model_snapshot')})
    write(OUT/'repair-review.pending.json',{'status':'pending','reviewed_at':None,
        'selection_plan_sha256':sha(OUT/'selection-plan.json'),'builder_sha256':sha(Path(__file__)),
        'predata':verify_predata(),'reviewed_file_sha256':{name:sha(MAIN/name) for name in REVIEW_INPUTS},
        'selected_replacement_units':selected,'selected_raw_verification_sha256':sha(OUT/'selected-raw-review.json'),
        'comparability':{'initial_actual_prompt_task_tools_sampling_and_alias_equal':True,
            'preserved_config_equal_and_predeclared_control_byte_text_contract_passed':True,'fingerprints':fingerprints,
            'actual_workers_by_cohort':{name:read(MAIN/'results'/name/'repair-protocol.json').get('actual_workers') for name in ['timing-repair-001','timing-repair-002']},
            'model_limit':'Same mutable alias/documented version does not prove identical model weights; fingerprint agreement is not an immutable model guarantee.'},
        'claim_boundary':'Pending independent lead review. Original/repair001 vetoes retained; conditional sensitivity only. Metadata copying erratum, later collection, actual worker count, alias/fingerprint drift and sampled clocks must remain disclosed.'})
    print(json.dumps({'prepared_review_only':True,'status':'pending','accepted':False,'view_created':False}))


def build(analyze=False):
    if VIEW.exists():raise ValueError('Transient view exists; preserve/inspect it rather than silently replace it')
    rows,base=selection()
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=FROZEN,text=True).strip()!='4ddfbe4a73922fcde360b3d68bd0d104cb3b0d70':raise ValueError('Wrong frozen analyzer checkout')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=FROZEN,text=True).strip():raise ValueError('Frozen analyzer checkout has tracked modifications')
    ledger=OUT/'selection-ledger.csv'
    with ledger.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    # Portable ledger uses repository-relative source paths; only transient plan is absolute.
    VIEW.mkdir(parents=True);(VIEW/'runs').mkdir()
    plan=MAIN/'.runtime/timing-amended-junction-plan.json'
    junctions=[{'link':str(VIEW/'runs'/r['source_run_id']),'target':str(MAIN/r['source_folder'])} for r in rows]
    junctions.append({'link':str(VIEW/'source'),'target':str(MAIN/'results/study-002/source')})
    write(plan,{'rows':junctions})
    if os.name=='nt':
        command="$ErrorActionPreference='Stop'; $p=Get-Content -Raw -LiteralPath $env:CSEC603_VIEW_PLAN | ConvertFrom-Json; foreach($r in $p.rows){New-Item -ItemType Junction -Path $r.link -Target $r.target | Out-Null}"
        subprocess.run([shutil.which('pwsh') or 'powershell.exe','-NoProfile','-NonInteractive','-Command',command],env={**os.environ,'CSEC603_VIEW_PLAN':str(plan)},check=True,capture_output=True,text=True)
    else:
        raise ValueError('This validated view design uses Windows junctions; other platforms need a reviewed loader adapter')
    for name in ['config.json','freeze.json']:(VIEW/name).write_bytes((MAIN/'results/timing-repair-001'/name).read_bytes())
    manifest={**base,'collection_name':'study-002-timing-sensitivity-001','created_at':time.time(),'original_created_at':base['created_at'],
      'amendment':'Conditional timing-repair view; not original frozen untouched collection','selection_ledger_sha256':sha(ledger),
      'original_manifest_sha256':sha(MAIN/'results/study-002/manifest.json'),'selection_plan_sha256':sha(OUT/'selection-plan.json')}
    write(VIEW/'manifest.json',manifest)
    overlay={'classification':'Conditional amended timing sensitivity analysis','selected_originals':1168,'selected_replacements':32,
      'portable_selection_ledger':'results/timing-sensitivity-001/selection-ledger.csv','selection_ledger_sha256':sha(ledger),
      'selection_plan_sha256':sha(OUT/'selection-plan.json'),'quality_review_file_sha256':read(OUT/'repair-review.json')['reviewed_file_sha256'],'review_sha256':sha(OUT/'repair-review.json'),
      'original_validation_remains_false':True,'structural_eligibility_alone_is_insufficient':True,
      'claim_limit':'Any hypotheses remain conditional on this declared amendment; original reports and invalid timing records remain unchanged.'}
    write(VIEW/'repair-overlay.json',overlay);write(OUT/'referenced-view.json',overlay)
    paths=list(VIEW.rglob('summary.json'))
    if len(paths)!=1200:raise ValueError('Frozen Python junction traversal does not expose exactly1200 summaries; do not analyze')
    # Always validate both original and replacement raw data, even without --analyze.
    verification=OUT/'view-raw-verification.json'
    program='import json,sys;from pathlib import Path;from analysis.cli import verify_raw;r=verify_raw(Path(sys.argv[1]));Path(sys.argv[2]).write_text(json.dumps(r,indent=2),encoding="utf-8");raise SystemExit(0 if r["valid"] else 2)'
    subprocess.run([sys.executable,'-c',program,str(VIEW),str(verification)],cwd=FROZEN,check=True)
    for r in rows:
        folder=MAIN/r['source_folder']
        if sha(folder/'summary.json')!=r['summary_sha256'] or sha(folder/'raw-manifest.json')!=r['raw_manifest_sha256']:
            raise ValueError('Selected source changed after selection ledger was hashed')
    overlay['selected_original_and_replacement_raw_verified']=True
    overlay['view_raw_verification_sha256']=sha(verification)
    write(VIEW/'repair-overlay.json',overlay);write(OUT/'referenced-view.json',overlay)
    if analyze:
        analysis=OUT/'analysis-amended';analysis.mkdir(exist_ok=True)
        (analysis/'AMENDMENT.md').write_text('# Conditional amended timing sensitivity analysis\n\nThis output uses1168 original units plus30 individually reviewed repair001 and two repair002 timing replacements. Original study-002 validation remains failed. Structural eligibility and hypothesis statuses from the unchanged frozen analyzer are conditional on the declared timing amendment and accepted repair quality; they are not claims that the original collection passed all gates. See referenced-view.json, selection-ledger.csv, repair-review.json and docs/timing-endpoint-repair-protocol.md.\n',encoding='utf-8')
        subprocess.run([sys.executable,'-m','analysis.cli','--input',str(VIEW),'--output',str(analysis),'--verify-raw'],cwd=FROZEN,check=True)
        assessment=analysis/'hypothesis-assessment.json'
        write(analysis/'conditional-hypothesis-assessment.json',{'interpretation':'Conditional amended timing sensitivity only; original validation remains false',
          'overlay':overlay,'unchanged_frozen_assessment_sha256':sha(assessment),'unchanged_frozen_assessment':read(assessment)})
    print(json.dumps({'view':str(VIEW),'units':len(paths),'raw_copies':0,'conditional_amendment':True,'analysis_requested':analyze}))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',action='store_true');p.add_argument('--analyze',action='store_true');p.add_argument('--prepare-review',action='store_true');a=p.parse_args()
    if a.prepare_review and (a.build or a.analyze):p.error('--prepare-review cannot accept/build/analyze')
    if a.prepare_review:prepare_review();return
    if a.analyze and not a.build:p.error('--analyze requires explicit --build')
    if a.build:build(a.analyze)
    else:print(json.dumps({'prepared_only':True,'view_created':False,'requires':'Predeclared32 replacements, all selected raw/endpoint/clock criteria and hash-bound accepted review'}))

if __name__=='__main__':main()
