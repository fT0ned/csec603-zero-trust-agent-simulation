"""Independent saved-evidence review; no acceptance, collection or view creation.

Run only after actual repair002 quality/endpoint files close. Writes this separate
review directory, which is outside the builder's acceptance REVIEW_INPUTS.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import xml.etree.ElementTree as ET

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def main():
    cohort=ROOT/'results/timing-repair-002'
    # Fail before writing any recommendation when final actual data are absent.
    for name in ['quality.json','endpoint-review.json','batch-status.json']:
        if not (cohort/name).is_file():raise FileNotFoundError('Final evidence not available: '+name)
    quality=read(cohort/'quality.json');status=read(cohort/'batch-status.json')
    builder=load(ROOT/'results/timing-sensitivity-001/build_referenced_view.py','independent_builder')
    rows,_=builder.selection(False)  # Read-only gates; no raw sweep/view/acceptance.
    endpoint=load(cohort/'adjudicate_endpoints.py','independent_endpoint');endpoint.ROOT=ROOT
    pins={};endpoints=[];raw_count=0;all_replacement_raw_count=0;errors=[]
    for row in rows:
        if not row['is_replacement']:continue
        folder=ROOT/row['source_folder']
        if row['source_collection']=='timing-repair-002':
            item=endpoint.audit_run(folder,pins);endpoints.append(item)
            errors.extend({'run_id':item['run_id'],'error':x} for x in item['issues'])
        manifest=read(folder/'raw-manifest.json')
        for name,expected in manifest['files'].items():
            path=(folder/name).resolve()
            if not path.is_relative_to(folder.resolve()):raise ValueError('Unsafe sealed path')
            actual=sha(path);pins[str(path.relative_to(ROOT))]=actual;all_replacement_raw_count+=1
            if row['source_collection']=='timing-repair-002':raw_count+=1
            if actual!=expected:errors.append({'run_id':row['source_run_id'],'error':'Raw byte mismatch: '+name})
    clocks=[json.loads(line) for line in (cohort/'clock-brackets.jsonl').read_text().splitlines()]
    gaps=[b['host_monotonic']-a['host_monotonic'] for a,b in zip(clocks,clocks[1:])]
    sample_failures=[]
    for i,bracket in enumerate(clocks):
        if not bracket.get('passed'):sample_failures.append({'index':i,'error':'Aggregate sample failure'})
        for sample in bracket.get('samples',[]):
            if abs(sample['offset_lower_seconds'])>1 or abs(sample['offset_upper_seconds'])>1 or abs(sample['host_epoch_minus_monotonic_delta_seconds'])>.05:
                sample_failures.append({'index':i,'service':sample['service'],'error':'Independent bracket bounds exceeded'})
    windows=read(cohort/'windows-clock-events.json');steps=[]
    for event in windows['events']:
        if event['provider']=='Microsoft-Windows-Kernel-General' and event['id']==1:
            data={x.attrib.get('Name'):x.text for x in ET.fromstring(event['xml']).iter() if x.tag.endswith('Data')}
            if abs(float(data.get('TimeDeltaInMs',0)))>=50:steps.append(event['record_id'])
    errors.extend(sample_failures)
    if not clocks or max(gaps,default=0)>15 or steps:errors.append({'error':'Clock monitoring incomplete or step/gap exceeded'})
    if quality.get('passed') is not True or quality.get('errors') or status.get('unexpected_errors') or status.get('completed')!=2:
        errors.append({'error':'Final recorded quality/batch gate did not pass'})
    selected=[]
    for row in rows:
        if not row['is_replacement']:continue
        old=read(ROOT/'results/study-002/runs'/row['original_run_id']/'summary.json');new=read(ROOT/row['source_folder']/'summary.json')
        selected.append({**{k:row[k] for k in ['source_collection','source_run_id','original_run_id','summary_sha256','raw_manifest_sha256']},
            'actual_model':new['metadata']['model_snapshot'],'original_fingerprints':sorted(set(old.get('system_fingerprints',[]))),
            'replacement_fingerprints':sorted(set(new.get('system_fingerprints',[])))})
    for name in builder.REVIEW_INPUTS:pins[name]=sha(ROOT/name)
    proof_path=ROOT/'results/timing-sensitivity-001/selected-raw-review.json';proof_review=None
    if proof_path.is_file():
        proof=read(proof_path)
        if proof.get('valid') is not True or proof.get('selected_units')!=rows or proof.get('runs')!=1200:
            errors.append({'error':'Lead-prepared selected raw proof is invalid or differs from independently selected1200 rows'})
        proof_review={'sha256':sha(proof_path),'valid':proof.get('valid'),'runs':proof.get('runs'),
                      'files_checked':proof.get('files_checked'),'selected_rows_exact_match':proof.get('selected_units')==rows,
                      'scope':'Proof inspected; all32 replacement raw files additionally rehashed independently, remaining original files not duplicated by this review.'}
    report={'reviewer':'Independent analysis agent /root/analysis','reviewed_at':datetime.now(timezone.utc).isoformat(),
        'review_signature_note':'Named agent review with source/script hashes; not a cryptographic identity signature or lead authorization.',
        'scope':'Independent postcompletion quality and comparability recommendation for prospective32-unit timing sensitivity',
        'recommendation':'Recommend lead consideration of the conditional sensitivity only, subject to complete1200 selected-raw verification and explicit hash-bound acceptance; original and repair001 vetoes remain.' if not errors else 'Do not accept; independent review found unresolved failures.',
        'errors':errors,'lead_acceptance_created':False,'view_created':False,'statistical_analysis_performed':False,
        'selected_source_counts':{n:sum(r['source_collection']==n for r in rows) for n in ['study-002','timing-repair-001','timing-repair-002']},
        'predata':builder.verify_predata(),'selected_replacements':selected,'repair002_endpoints':endpoints,
        'repair002_raw_files_independently_checked':raw_count,
        'all32_replacement_raw_files_independently_checked':all_replacement_raw_count,
        'selected1200_raw_proof_review':proof_review,
        'clock_checks':{'samples':len(clocks),'max_gap_seconds':max(gaps,default=None),'independent_sample_failures':sample_failures,'significant_host_step_records':steps},
        'worker_evidence':{n:builder.dispatcher_worker_evidence(n) for n in ['timing-repair-001','timing-repair-002']},
        'limitations':['Later collection and worker counts31/2 versus original32 limit exchangeability.',
          'Same mutable alias/fingerprint does not establish identical model weights.',
          'Sampled brackets and Windows logs cannot prove perfect continuous synchronization.',
          'Frozen002 metadata copying errors remain preserved/disclosed through the hashed clarification.',
          'Original/repair001 tool failures are not silently recoded as noninformative censoring.',
          'Timing sensitivity cannot establish unexercised real-LLM harmful-action prevention in S2/S5.',
          'This reviewer directly rehashed all32 selected replacement archives; complete1200 selected raw proof is inspected separately when available.'],
        'source_hashes':pins,'review_script_sha256':sha(Path(__file__))}
    target=OUT/'reviewer-report.json';target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (OUT/'reviewer-report.sha256').write_text(sha(target)+'  reviewer-report.json\n',encoding='ascii')
    print(json.dumps({'errors':len(errors),'recommendation':report['recommendation'],'lead_acceptance_created':False,'view_created':False}))

if __name__=='__main__':main()
