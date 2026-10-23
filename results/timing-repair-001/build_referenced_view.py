"""Build a transient zero-copy amended view only after explicit repair review.

No default action. --build needs accepted repair-review.json bound to quality and
protocol hashes. Raw bytes are never copied, modified or removed. --analyze is
optional and invokes the unchanged analyzer from the frozen worktree.
"""
import argparse,csv,hashlib,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
OUT=Path(__file__).resolve().parent
MAIN=OUT.parents[1]
VIEW=MAIN/'.runtime/timing-amended-view'
FROZEN=MAIN.parent/'GithubRepoFrozenTimingV2'
FIELDS=['condition','scenario','ttl_seconds','revocation_mode','seed','pair_id']
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def key(r):return tuple(r[k] for k in FIELDS)

def selection():
    protocol=read(OUT/'repair-protocol.json');quality=read(OUT/'quality.json');review=read(OUT/'repair-review.json')
    if not quality.get('passed') or review.get('status')!='accepted':raise ValueError('Repair quality and explicit lead review must pass first')
    if review.get('quality_sha256')!=sha(OUT/'quality.json') or review.get('protocol_sha256')!=sha(OUT/'repair-protocol.json'):
        raise ValueError('Review does not bind current quality/protocol bytes')
    links=[json.loads(line) for line in (OUT/'replacement-links.jsonl').read_text().splitlines()]
    if len(links)!=31 or len({x['original_run_id'] for x in links})!=31 or any(x['status']!='completed' for x in links):raise ValueError('Require31 unique successful linked attempts')
    by_original={x['original_run_id']:x for x in links};declared={x['original_run_id']:x for x in protocol['links']}
    if set(by_original)!=set(declared):raise ValueError('Replacement set differs from predeclared clock scope')
    original=MAIN/'results/study-002';manifest=read(original/'manifest.json')
    completed={}
    for p in original.glob('runs/*/summary.json'):
        r=read(p)
        if r['status']=='completed':
            if key(r) in completed:raise ValueError('Original duplicate terminal cell requires explicit review')
            completed[key(r)]=(p,r)
    if len(completed)!=1200:raise ValueError('Original terminal matrix is incomplete')
    output=[]
    for cell in manifest['cells']:
        p,r=completed[key(cell)];original_id=r['run_id'];replacement=by_original.get(original_id)
        if replacement:
            if sha(p)!=declared[original_id]['original_summary_sha256']:raise ValueError('Original declared summary hash changed')
            if key(replacement['cell'])!=key(cell):raise ValueError('Replacement cell mismatch')
            rid=replacement['replacement_run_id'];p=OUT/'runs'/rid/'summary.json';r=read(p)
            if key(r)!=key(cell) or r['status']!='completed':raise ValueError('Replacement summary mismatch')
        folder=p.parent.resolve()
        if not re.fullmatch(r'r[0-9a-f]{32}',r['run_id']):raise ValueError('Unsafe run ID')
        permitted=(OUT/'runs').resolve() if replacement else (original/'runs').resolve()
        if not folder.is_relative_to(permitted):raise ValueError('Selected run escapes its original cohort')
        output.append({**cell,'source_collection':'timing-repair-001' if replacement else 'study-002','source_run_id':r['run_id'],
          'source_folder':folder.relative_to(MAIN).as_posix(),'summary_sha256':sha(p),'raw_manifest_sha256':sha(folder/'raw-manifest.json'),
          'original_run_id':original_id,'is_replacement':bool(replacement)})
    if len(output)!=1200 or sum(x['is_replacement'] for x in output)!=31:raise ValueError('Selection must be1169 originals plus31 replacements')
    return output,manifest

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
    for name in ['config.json','freeze.json']:(VIEW/name).write_bytes((OUT/name).read_bytes())
    manifest={**base,'collection_name':'study-002-timing-amended','created_at':time.time(),'original_created_at':base['created_at'],
      'amendment':'Conditional timing-repair view; not original frozen untouched collection','selection_ledger_sha256':sha(ledger),
      'original_manifest_sha256':sha(MAIN/'results/study-002/manifest.json'),'repair_manifest_sha256':sha(OUT/'manifest.json')}
    write(VIEW/'manifest.json',manifest)
    overlay={'classification':'Conditional amended timing sensitivity analysis','selected_originals':1169,'selected_replacements':31,
      'portable_selection_ledger':'results/timing-repair-001/selection-ledger.csv','selection_ledger_sha256':sha(ledger),
      'repair_protocol_sha256':sha(OUT/'repair-protocol.json'),'quality_sha256':sha(OUT/'quality.json'),'review_sha256':sha(OUT/'repair-review.json'),
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
        (analysis/'AMENDMENT.md').write_text('# Conditional amended timing sensitivity analysis\n\nThis output uses1169 original units plus31 predeclared timing replacements. Original study-002 validation remains failed. Structural eligibility and hypothesis statuses from the unchanged frozen analyzer are conditional on the declared timing amendment and accepted repair quality; they are not claims that the original collection passed all gates. See referenced-view.json, selection-ledger.csv, repair-review.json and docs/timing-repair-protocol.md.\n',encoding='utf-8')
        subprocess.run([sys.executable,'-m','analysis.cli','--input',str(VIEW),'--output',str(analysis),'--verify-raw'],cwd=FROZEN,check=True)
        assessment=analysis/'hypothesis-assessment.json'
        write(analysis/'conditional-hypothesis-assessment.json',{'interpretation':'Conditional amended timing sensitivity only; original validation remains false',
          'overlay':overlay,'unchanged_frozen_assessment_sha256':sha(assessment),'unchanged_frozen_assessment':read(assessment)})
    print(json.dumps({'view':str(VIEW),'units':len(paths),'raw_copies':0,'conditional_amendment':True,'analysis_requested':analyze}))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',action='store_true');p.add_argument('--analyze',action='store_true');a=p.parse_args()
    if a.analyze and not a.build:p.error('--analyze requires explicit --build')
    if a.build:build(a.analyze)
    else:print(json.dumps({'prepared_only':True,'view_created':False,'requires':'Completed31 repair units + quality passed + lead-accepted hash-bound repair-review.json'}))

if __name__=='__main__':main()
