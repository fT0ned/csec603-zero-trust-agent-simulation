"""Build a transient zero-copy amended view only after explicit repair review.

No default action. --build needs accepted repair-review.json bound to quality and
protocol hashes. Raw bytes are never copied, modified or removed. --analyze is
optional and invokes the unchanged analyzer from the frozen worktree.
"""
import argparse,csv,hashlib,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
OUT=Path(__file__).resolve().parent
MAIN=OUT.parents[1]
VIEW=MAIN/'.runtime/timing-sensitivity-001-view'
FROZEN=MAIN.parent/'GithubRepoFrozenTimingV2'
FIELDS=['condition','scenario','ttl_seconds','revocation_mode','seed','pair_id']
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def key(r):return tuple(r[k] for k in FIELDS)

def selection():
    plan=read(OUT/'selection-plan.json');review=read(OUT/'repair-review.json')
    if review.get('status')!='accepted' or review.get('selection_plan_sha256')!=sha(OUT/'selection-plan.json'):
        raise ValueError('Require accepted review bound to predeclared selection plan')
    required=['results/timing-repair-001/quality.json','results/timing-repair-001/quality-adjudication.json',
              'results/quality-study002/quality-adjudication.json','results/timing-repair-002/quality.json']
    if set(review.get('reviewed_file_sha256',{}))!=set(required):raise ValueError('Review must bind all applicable assessments')
    for name in required:
        if review['reviewed_file_sha256'][name]!=sha(MAIN/name):raise ValueError('Reviewed quality bytes changed')
    if not read(MAIN/required[0]).get('passed') or not read(MAIN/required[3]).get('passed'):
        raise ValueError('Both repair clock/raw gates must pass; repair002 also includes endpoint gate')
    original_review=read(MAIN/required[2]);repair_review=read(MAIN/required[1])
    if not original_review.get('audit_complete') or not repair_review.get('audit_complete'):raise ValueError('Endpoint audits incomplete')
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
            source=choice['replacement_collection'];link=candidates[source][original_id]
            if link['status']!='completed' or key(link['cell'])!=key(cell):raise ValueError('Replacement mismatch')
            if sha(path)!=link['original_summary_sha256']:raise ValueError('Original source changed')
            path=MAIN/'results'/source/'runs'/link['replacement_run_id']/'summary.json';row=read(path)
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
    return rows,manifest


def build(analyze=False):
    if VIEW.exists():raise ValueError('Transient view exists; preserve/inspect it rather than silently replace it')
    rows,base=selection()
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=FROZEN,text=True).strip()!='4ddfbe4a73922fcde360b3d68bd0d104cb3b0d70':raise ValueError('Wrong frozen analyzer checkout')
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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',action='store_true');p.add_argument('--analyze',action='store_true');a=p.parse_args()
    if a.analyze and not a.build:p.error('--analyze requires explicit --build')
    if a.build:build(a.analyze)
    else:print(json.dumps({'prepared_only':True,'view_created':False,'requires':'Predeclared32 replacements, all selected raw/endpoint/clock criteria and hash-bound accepted review'}))

if __name__=='__main__':main()
