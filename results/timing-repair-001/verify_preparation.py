"""Focused temporary-fixture checks; never start collection or contact a provider."""
import gzip,hashlib,importlib.util,json,os,shutil,subprocess,tempfile
from pathlib import Path

def main():
    here=Path(__file__).resolve().parent
    spec=importlib.util.spec_from_file_location('prepared_repair',here/'collect_repair.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='csec603-repair-clock-check-') as directory:
        folder=Path(directory)
        for name,times in [('probes.jsonl.gz',[100,101]),('probes-0001.jsonl.gz',[102,103]),
                           ('probes-0002.jsonl.gz',[104,103.5]),('probes-0003.jsonl.gz',[103.4,105])]:
            with gzip.open(folder/name,'wt') as f:
                for t in times:f.write(json.dumps({'time':t})+'\n')
        errors=module.probe_time_reversals(folder,'temporary-unit-fixture')
        assert len(errors)==2,errors
        assert errors[0]['probe_file']=='probes-0002.jsonl.gz' and errors[0]['line']==2
        assert errors[1]['probe_file']=='probes-0003.jsonl.gz' and errors[1]['line']==1
    clean={'planned':31,'completed':31,'remaining_failures':0,'unexpected_errors':[]}
    assert not module.batch_quality_errors(clean)
    assert module.batch_quality_errors({**clean,'unexpected_errors':[{'clock_event_capture_error':'RuntimeError'}]})
    assert module.batch_quality_errors({**clean,'remaining_failures':1})
    with tempfile.TemporaryDirectory(prefix='csec603-repair-source-check-') as directory:
        root=Path(directory);captured=root/'captured';frozen=root/'frozen';captured.mkdir();frozen.mkdir()
        (captured/'client.py').write_bytes(b"print('fixture')\r\n")
        (frozen/'client.py').write_bytes(b"print('fixture')\n")
        h=hashlib.sha256((captured/'client.py').read_bytes()).hexdigest()
        assert module.compare_deployed_sources({'client.py':h},captured,frozen,{'client.py':h})['passed']
        assert not module.compare_deployed_sources({'client.py':'0'*64},captured,frozen,{'client.py':h})['passed']
        (captured/'client.py').write_bytes(b"print('changed code')\r\n")
        changed=hashlib.sha256((captured/'client.py').read_bytes()).hexdigest()
        assert not module.compare_deployed_sources({'client.py':changed},captured,frozen,{'client.py':changed})['passed']
    from analysis.run import load_runs
    from analysis.cli import verify_raw
    with tempfile.TemporaryDirectory(prefix='csec603-repair-junction-check-') as directory:
        root=Path(directory).resolve();source=root/'raw'/'unit';source.mkdir(parents=True)
        view=root/'view';(view/'runs').mkdir(parents=True);link=view/'runs'/'unit'
        summary=source/'summary.json';summary.write_text(json.dumps({'condition':'C2','scenario':'S1','mode':'scripted',
          'phase':'engineering','status':'completed','run_id':'temporary-junction-fixture','model':'fixture','model_snapshot':'fixture'}),encoding='utf-8')
        (source/'raw-manifest.json').write_text(json.dumps({'hash_scheme':'sha256-bytes','files':{'summary.json':hashlib.sha256(summary.read_bytes()).hexdigest()}}))
        (view/'manifest.json').write_text(json.dumps({'collection_name':'junction-fixture'}));(view/'config.json').write_text('{}')
        assert source.is_relative_to(root) and link.parent.resolve().is_relative_to(root)
        command="$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path $env:CSEC603_FIXTURE_LINK -Target $env:CSEC603_FIXTURE_SOURCE | Out-Null"
        subprocess.run([shutil.which('pwsh') or 'powershell.exe','-NoProfile','-NonInteractive','-Command',command],
          env={**os.environ,'CSEC603_FIXTURE_LINK':str(link),'CSEC603_FIXTURE_SOURCE':str(source)},capture_output=True,text=True,check=True)
        try:
            paths=list(view.rglob('summary.json'));assert len(paths)==1 and paths[0].resolve()==summary.resolve(),paths
            records,sources,errors=load_runs(view)
            assert not errors and len(records)==1,(records,errors)
            assert records[0]['collection_root']==str(view.resolve())
            assert records[0]['collection_id'].startswith('junction-fixture-')
            assert records[0]['source_path']==str(summary.resolve())
            seals=verify_raw(view);assert seals['valid'] and seals['files_checked']==1,seals
        finally:
            # Remove only the junction itself before scoped temporary-tree cleanup.
            os.rmdir(link)
    checks={'classification':'Temporary-fixture software checks only; no experimental units/provider calls',
      'rotated_probe_internal_reversal_detected':True,'rotation_boundary_reversal_detected':True,
      'clean_batch_status_accepted':True,'final_clock_query_error_vetoes_quality':True,
      'remaining_failure_vetoes_quality':True,'python312_rglob_traverses_windows_junction':True,
      'frozen_loader_uses_view_lexical_collection_context':True,'frozen_loader_resolves_original_source_path':True,
      'frozen_raw_verifier_accepts_scoped_junction_read':True,'passed':True,'experiment_started':False,'provider_calls':0}
    checks.update({'captured_CRLF_frozen_LF_semantics_accepted':True,'deployed_byte_change_rejected':True,'non_newline_source_change_rejected':True})
    print(json.dumps(checks))
    return checks

if __name__=='__main__':main()
