"""Explicitly gated 2-cell repair using unchanged study-freeze-v2 run_one.

Without --execute this performs static preparation checks only. Never run concurrently
with another collection. The parent/operator must clear execution first.
"""
from __future__ import annotations
import argparse,concurrent.futures,datetime,gzip,hashlib,json,os,shutil,sqlite3,subprocess,sys,threading,time,xml.etree.ElementTree as ET
from pathlib import Path

OUT=Path(__file__).resolve().parent
MAIN=OUT.parents[1]
FROZEN=MAIN.parent/'GithubRepoFrozenTimingV2'
sys.path.insert(0,str(FROZEN))
from testbed.common import ROOT,write_json,canonical
from testbed.runner import validate_config,run_one
from testbed.power import keep_awake

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def append(path,item):
    with path.open('a',encoding='utf-8') as f:
        f.write(json.dumps(item,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())

def windows_events(start):
    # All inputs are numeric epochs; never interpolate credentials or request bodies.
    command=("$ErrorActionPreference='Stop'; $s=[DateTimeOffset]::FromUnixTimeSeconds("+str(int(start)-2)+
      ").LocalDateTime; try {$events=Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=$s} -ErrorAction Stop} "
      "catch {if($_.FullyQualifiedErrorId -notlike 'NoMatchingEventsFound*'){throw};$events=@()}; $e=$events | "
      "Where-Object {($_.ProviderName -eq 'Microsoft-Windows-Kernel-General' -and $_.Id -eq 1) -or $_.ProviderName -eq 'Microsoft-Windows-Time-Service'} | "
      "ForEach-Object { [pscustomobject]@{utc=$_.TimeCreated.ToUniversalTime().ToString('o');provider=$_.ProviderName;id=$_.Id;record_id=$_.RecordId;message=$_.Message;xml=$_.ToXml()} }; ConvertTo-Json -InputObject @($e) -Depth 4")
    p=subprocess.run([shutil.which('pwsh') or 'powershell.exe','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=20)
    if p.returncode:raise RuntimeError('Windows clock-event query failed')
    return json.loads(p.stdout or '[]')

def clock_sample():
    import httpx
    samples=[]
    for name,url in [('gateway','http://127.0.0.1:8766/health'),('pa','http://127.0.0.1:8767/health')]:
        before=time.time();mono=time.monotonic()
        with httpx.Client(timeout=5,trust_env=False) as client:
            response=client.get(url);response.raise_for_status();health=response.json();remote=health['time']
        after=time.time();elapsed=time.monotonic()-mono
        samples.append({'service':name,'host_before':before,'host_after':after,'remote_time':remote,
          'offset_lower_seconds':remote-after,'offset_upper_seconds':remote-before,
          'roundtrip_monotonic_seconds':elapsed,'host_epoch_minus_monotonic_delta_seconds':after-before-elapsed,
          'active_runs':health.get('active_runs')})
    before=time.time();mono=time.monotonic()
    p=subprocess.run(['docker','compose','exec','-T','attacker','python','-c',
       'import json,time;print(json.dumps({"time":time.time(),"monotonic":time.monotonic()}))'],cwd=FROZEN,capture_output=True,text=True,timeout=10)
    after=time.time();elapsed=time.monotonic()-mono
    if p.returncode:raise RuntimeError('Attacker clock query failed')
    remote=json.loads(p.stdout)
    samples.append({'service':'attacker','host_before':before,'host_after':after,'remote_time':remote['time'],
       'remote_monotonic':remote['monotonic'],'offset_lower_seconds':remote['time']-after,
       'offset_upper_seconds':remote['time']-before,'roundtrip_monotonic_seconds':elapsed,
       'host_epoch_minus_monotonic_delta_seconds':after-before-elapsed})
    for s in samples:
        s['passed']=max(abs(s['offset_lower_seconds']),abs(s['offset_upper_seconds']))<=1 and abs(s['host_epoch_minus_monotonic_delta_seconds'])<=.05
    return {'host_time':time.time(),'host_monotonic':time.monotonic(),'samples':samples,'passed':all(s['passed'] for s in samples)}

def compare_deployed_sources(actual,captured,frozen,expected_hashes):
    details={}
    for name,h in actual.items():
        original=captured/name;tagged=frozen/name
        captured_hash=sha(original)
        normalized_original=original.read_text(encoding='utf-8')
        normalized_frozen=tagged.read_text(encoding='utf-8')
        details[name]={'deployed_sha256':h,'captured_sha256':captured_hash,'frozen_checkout_byte_sha256':sha(tagged),
          'deployed_matches_captured_bytes':h==captured_hash,
          'captured_matches_predeclared_hash':captured_hash==expected_hashes.get(name),
          'captured_and_frozen_normalized_text_equal':normalized_original==normalized_frozen,
          'normalized_text_sha256':hashlib.sha256(normalized_original.encode('utf-8')).hexdigest()}
    return {'hashes':actual,'files':details,
      'comparison_contract':'Actual image bytes must match original captured study002 source bytes and predeclared hash; captured UTF8 universal-newline text must equal frozen checkout text. No source bytes rewritten.',
      'passed':bool(details) and set(actual)==set(expected_hashes) and all(d['deployed_matches_captured_bytes'] and d['captured_matches_predeclared_hash'] and d['captured_and_frozen_normalized_text_equal'] for d in details.values())}

def deployed_sources():
    paths=['testbed/service.py','testbed/client.py','testbed/common.py','testbed/fixtures.py','infra/tools.py']
    program='import json,hashlib,pathlib;print(json.dumps({p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in '+repr(paths)+'}))'
    p=subprocess.run(['docker','compose','exec','-T','pa','python','-c',program],cwd=FROZEN,capture_output=True,text=True,timeout=20,check=True)
    actual=json.loads(p.stdout)
    protocol=json.loads((OUT/'repair-protocol.json').read_text(encoding='utf-8'))
    report=compare_deployed_sources(actual,MAIN/'results/study-002/source',FROZEN,protocol['deployed_source_contract']['captured_byte_sha256'])
    report['original_manifest_hash_matches']=sha(MAIN/'results/study-002/manifest.json')==protocol['deployed_source_contract']['original_study_manifest_sha256']
    report['passed']=report['passed'] and report['original_manifest_hash_matches']
    return report

def static_checks():
    protocol=json.loads((OUT/'repair-protocol.json').read_text(encoding='utf-8'))
    manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
    config=json.loads((OUT/'config.json').read_text(encoding='utf-8'))
    if ROOT!=FROZEN:raise RuntimeError('Wrong runtime module root')
    if len(manifest['cells'])!=2 or len({canonical(x) for x in manifest['cells']})!=2:raise RuntimeError('Repair requires exact2 distinct cells')
    if sha(OUT/'collect_repair.py')!=protocol['launcher_sha256']:raise RuntimeError('Prepared launcher changed')
    if sha(OUT/'config.json')!=protocol['config_sha256']:raise RuntimeError('Original configuration changed')
    if sha(OUT/'manifest.json')!=protocol['manifest_sha256']:raise RuntimeError('Prepared cell manifest changed')
    original={'runs':protocol['links']}
    fields=['condition','scenario','ttl_seconds','revocation_mode','seed','pair_id']
    key=lambda x:tuple(x[k] for k in fields)
    if {key(x) for x in manifest['cells']}!={key(x) for x in original['runs']}:raise RuntimeError('Repair differs from declared2 event-overlap cells')
    if (FROZEN/'.runtime').resolve()!=(MAIN/'.runtime').resolve():raise RuntimeError('Shared runtime/aggregate ledger not linked')
    if sha(OUT/'adjudicate_endpoints.py')!=protocol['endpoint_helper_sha256']:raise RuntimeError('Endpoint helper changed')
    # Full frozen validation: config, all frozen source, analysis plan and pushed tag.
    validate_config(config)
    for name,h in manifest['source_sha256'].items():
        if sha(OUT/'source'/name)!=h or sha(FROZEN/name)!=h:raise RuntimeError('Captured frozen source changed: '+name)
    return protocol,manifest,config

def probe_time_reversals(folder,run_id):
    paths=sorted(folder.glob('probes*.jsonl.gz'),key=lambda p:(p.name!='probes.jsonl.gz',p.name))
    if not paths or paths[0].name!='probes.jsonl.gz':raise FileNotFoundError('Initial probe file missing')
    previous=None;negative=[]
    for p in paths:
        with gzip.open(p,'rt') as f:
            for line_number,line in enumerate(f,1):
                x=json.loads(line)
                if previous is not None and x['time']<previous:
                    negative.append({'run_id':run_id,'probe_file':p.name,'line':line_number,'previous_time':previous,'time':x['time']})
                previous=x['time']
    return negative

def batch_quality_errors(status):
    errors=[]
    if status.get('unexpected_errors'):errors.append('Batch status contains unexpected errors, including any final clock-query failure')
    if status.get('planned')!=2 or status.get('completed')!=2 or status.get('remaining_failures')!=0:
        errors.append('Batch status is incomplete or has remaining failures')
    return errors

def assess_quality():
    rows=[json.loads(p.read_text(encoding='utf-8')) for p in OUT.glob('runs/*/summary.json')]
    errors=[];negative=[]
    if len(rows)!=2 or any(r['status']!='completed' for r in rows):errors.append('Repair subset lacks2 completed units; failures retained with no retry')
    for r in rows:
        if abs(r.get('theft_schedule_error_seconds',float('inf')))>1:errors.append(r['run_id']+': frozen handoff tolerance exceeded')
        try:negative.extend(probe_time_reversals(OUT/'runs'/r['run_id'],r['run_id']))
        except FileNotFoundError:errors.append(r['run_id']+': probe file missing')
    if negative:errors.append('Backward client timestamp detected')
    brackets=[json.loads(line) for line in (OUT/'clock-brackets.jsonl').read_text().splitlines()]
    if not brackets or any(not x.get('passed') for x in brackets):errors.append('Clock bracket failure/missing sample')
    maxgap=max((b['host_monotonic']-a['host_monotonic'] for a,b in zip(brackets,brackets[1:]) if 'host_monotonic' in a and 'host_monotonic' in b),default=0)
    if maxgap>15:errors.append('Clock monitoring gap exceeds15seconds')
    steps=[]
    for e in json.loads((OUT/'windows-clock-events.json').read_text())['events']:
        if e['provider']=='Microsoft-Windows-Kernel-General' and e['id']==1:
            data={x.attrib.get('Name'):x.text for x in ET.fromstring(e['xml']).iter() if x.tag.endswith('Data')}
            if abs(float(data.get('TimeDeltaInMs',0)))>=50:steps.append(e)
    if steps:errors.append('Windows clock step >=50ms during monitored interval')
    if (OUT/'monitor-errors.jsonl').exists():errors.append('Windows event monitoring error')
    errors.extend(batch_quality_errors(json.loads((OUT/'batch-status.json').read_text())))
    from analysis.cli import verify_raw
    seals=verify_raw(OUT)
    if not seals['valid']:errors.append('Repair raw integrity failure')
    import importlib.util
    spec=importlib.util.spec_from_file_location('endpoint_review',OUT/'adjudicate_endpoints.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=MAIN
    semantic=[];pins={}
    for r in rows:
        try:
            item=module.audit_run(OUT/'runs'/r['run_id'],pins);semantic.append(item)
            if item['issues']:errors.append(r['run_id']+': endpoint semantic failure')
        except Exception as error:errors.append(r['run_id']+': endpoint review '+type(error).__name__)
    write_json(OUT/'endpoint-review.json',{'runs':semantic,'source_hashes':pins,'helper_sha256':sha(OUT/'adjudicate_endpoints.py')})
    write_json(OUT/'quality.json',{'passed':not errors,'scope':'2-cell repair quality only; not complete1200-study eligibility',
       'errors':errors,'negative_probe_timestamps':negative,'significant_windows_steps':steps,'clock_sample_count':len(brackets),
       'maximum_clock_sample_gap_seconds':maxgap,'raw_verification':seals,
       'limitations':'Clock samples bound offsets only at observation times; absence of detected events is not proof of perfect continuous synchronization.'})

def collect():
    protocol,manifest,config=static_checks()
    if (OUT/'started.json').exists() or (OUT/'runs').exists():raise RuntimeError('Already started: one attempt per cell, never resume by repeating')
    preflight={'time':time.time(),'deployed_sources':deployed_sources(),'clock':clock_sample()}
    for service,binary,socket in [('spire-agent','spire-agent','/run/spire/sockets/agent.sock'),('spire-server','spire-server','/run/spire/server/api.sock')]:
        p=subprocess.run(['docker','compose','exec','-T',service,'/opt/spire/bin/'+binary,'healthcheck','-socketPath',socket],cwd=FROZEN,capture_output=True,text=True,timeout=15)
        preflight[service]={'passed':p.returncode==0}
    preflight['windows_events']=windows_events(preflight['time'])
    preflight['no_active_pa_tasks']=all(s.get('active_runs')==0 for s in preflight['clock']['samples'] if s['service']=='pa')
    write_json(OUT/'preflight.json',preflight)
    if not all([preflight['deployed_sources']['passed'],preflight['clock']['passed'],preflight['spire-agent']['passed'],preflight['spire-server']['passed'],preflight['no_active_pa_tasks']]):raise RuntimeError('Repair preflight failed; no experimental unit started')
    start=time.time();stop=threading.Event();errors=[]
    write_json(OUT/'started.json',{'time':start,'protocol_sha256':sha(OUT/'repair-protocol.json'),'source_tag':'study-freeze-v2','scope':'2-cell repair subset; not1200-unit full study','one_attempt_per_cell':True})
    def monitor():
        last_events=0
        while not stop.is_set():
            try:append(OUT/'clock-brackets.jsonl',clock_sample())
            except Exception as e:append(OUT/'clock-brackets.jsonl',{'time':time.time(),'passed':False,'error_type':type(e).__name__})
            if time.monotonic()-last_events>=30:
                try:write_json(OUT/'windows-clock-events.json',{'queried_at':time.time(),'events':windows_events(start)})
                except Exception as e:append(OUT/'monitor-errors.jsonl',{'time':time.time(),'error_type':type(e).__name__})
                last_events=time.monotonic()
            stop.wait(5)
    thread=threading.Thread(target=monitor,name='repair-clock-monitor',daemon=True);thread.start()
    count=0;links={x['original_run_id']:x for x in protocol['links']}
    fields=['condition','scenario','ttl_seconds','revocation_mode','seed','pair_id']
    lookup={tuple(x[k] for k in fields):x for x in protocol['links']}
    try:
        with keep_awake(),concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures={pool.submit(run_one,cell,config,OUT):cell for cell in manifest['cells']}
            for future in concurrent.futures.as_completed(futures):
                cell=futures[future];original=lookup[tuple(cell[k] for k in fields)]
                try:
                    row=future.result()
                    append(OUT/'replacement-links.jsonl',{'original_collection':'study-002','original_run_id':original['original_run_id'],'original_summary_sha256':original['original_summary_sha256'],
                       'replacement_run_id':row['run_id'],'status':row['status'],'attempt':1,'reason':'prespecified tool-failure endpoint infrastructure repair','cell':cell})
                except Exception as e:
                    errors.append({'original_run_id':original['original_run_id'],'error_type':type(e).__name__})
                count+=1;write_json(OUT/'progress.json',{'terminal_futures':count,'planned_repair_units':2,'unexpected_errors':errors,'time':time.time()})
    finally:
        stop.set();thread.join(timeout=40)
        try:write_json(OUT/'windows-clock-events.json',{'queried_at':time.time(),'events':windows_events(start)})
        except Exception as e:errors.append({'clock_event_capture_error':type(e).__name__})
        rows=[json.loads(p.read_text(encoding='utf-8')) for p in OUT.glob('runs/*/summary.json')]
        completed=sum(r['status']=='completed' for r in rows)
        write_json(OUT/'batch-status.json',{'planned':2,'planned_repair_units':2,'terminal_futures':count,'completed':completed,
          'remaining_failures':max(2-completed,len(errors)),
          'remaining_failures_definition':'Maximum of noncompleted planned units and unexpected-error count; global clock capture errors also prevent a clean status.',
          'infrastructure_failures':sum(r['status']=='infrastructure_failure' for r in rows),'unexpected_errors':errors,'finished_at':time.time(),
          'scope':'Repair subset only; original1200-unit collection unchanged. Completeness and clock quality require separate review.','automatic_retries':0})
        try:assess_quality()
        except Exception as e:write_json(OUT/'quality.json',{'passed':False,'scope':'Repair subset only','error_type':type(e).__name__,'reason':'Quality assessment could not finish; no inferred pass'})
    print(json.dumps({'repair_futures':count,'scope':'2-cell subset; no full-study eligibility claim','errors':errors}))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if args.execute:collect()
    else:
        _,manifest,_=static_checks()
        print(json.dumps({'prepared_cells':len(manifest['cells']),'started':False,'runtime_root':str(ROOT),'next':'Await lead clearance; --execute is the only experiment entry point.'}))

if __name__=='__main__':main()
