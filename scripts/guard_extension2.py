"""Supervise the frozen collector; resume only sealed transient HTTP failures.

This adds no cells, changes no result and never repeats a cell itself. The frozen
collector owns all sampling and its maximum-one-linked-repeat rule. Other errors
return for engineering inspection rather than being retried indiscriminately.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from testbed.common import ROOT,write_json
from testbed.power import keep_awake
from testbed.extension2.study import read,load_runs,verify_freeze
from testbed.extension2.preflight import verify


def status(stage,**extra):
    progress=ROOT/'results/extension-study-002/progress.json'
    value={'stage':stage,'updated_at':time.time(),**(read(progress) if progress.exists() else {}),**extra}
    write_json(ROOT/'.runtime/extension2/guardian-status.json',value)
    print(json.dumps(value,separators=(',',':')),flush=True)


def wait_existing(pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
    kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=kernel.OpenProcess(0x00100000,False,pid)
    if not handle:return
    try:
        while kernel.WaitForSingleObject(handle,0)==258:
            status('watching-existing-collector',collector_pid=pid)
            time.sleep(30)
    finally:kernel.CloseHandle(handle)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid',type=int,required=True);parser.add_argument('--log',type=Path,required=True)
    args=parser.parse_args();current_log=args.log;attempt=1
    with keep_awake():
        wait_existing(args.pid)
        while True:
            content=current_log.read_text(encoding='utf-8',errors='replace')
            output=ROOT/'results/extension-study-002'
            if (output/'quality.json').exists():
                raw,primary=load_runs(output)
                if len(primary)!=len(read(output/'manifest.json')):raise RuntimeError('Incomplete primary matrix with quality marker')
                status('collection-finished',raw=len(raw),primary=len(primary))
                for command in ([sys.executable,'-m','analysis.study002','--input',str(output)],
                                [sys.executable,'-m','scripts.closeout_extension2'],
                                [sys.executable,'-m','analysis.study002_report']):
                    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
                    if result.returncode:
                        (ROOT/'.runtime/extension2/postcollection-error.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
                        status('postcollection-inspection-required',module=command[2]);return
                status('analysis-closeout-report-ready');return
            if 'sealed infrastructure failure; restore infrastructure then resume pending matrix and single linked rerun' not in content:
                status('inspection-required',reason='Collector ended without complete quality marker or known sealed-infrastructure stop');return
            raw,primary=load_runs(output)
            last=max(raw,key=lambda r:r['finished_at'])
            if last['status']!='infrastructure_failure' or last.get('error_type') not in ('HTTPStatusError','RemoteProtocolError','ReadTimeout','ConnectError','ReadError'):
                status('inspection-required',reason='Failure is not an eligible transient HTTP transport fault',cell_id=last['cell_id'],error_type=last.get('error_type'));return
            verify_freeze(read(ROOT/'configs/extension-study-002.json'))
            preflight=verify(read(ROOT/'configs/extension-study-002.json'))
            incidents=ROOT/'docs/extension-study-002-infrastructure-incidents.json'
            values=read(incidents) if incidents.exists() else []
            if last['cell_id'] not in {r['cell_id'] for r in values}:
                values.append({'cell_id':last['cell_id'],'run_id':last.get('run_id'),
                    'started_at':last['started_at'],'finished_at':last['finished_at'],
                    'error_type':last.get('error_type'),
                    'root_cause':'Frozen collector sealed transient HTTP infrastructure error; inspect service trace for precise peer/path.',
                    'adjudication':'Retain original, resume pending matrix only; frozen collector schedules maximum one linked repeat independent of outcome.',
                    'restoration':'All19services healthy; source/model/boundary/clock preflight passes; no experiment changes.',
                    'preflight_checked_at':preflight['checked_at'],'resumed_at':time.time()})
                write_json(incidents,values)
            attempt+=1;current_log=ROOT/f'.runtime/extension2/full-guard-resume{attempt}-{uuid.uuid4().hex[:8]}.log'
            with current_log.open('w',encoding='utf-8') as stream:
                child=subprocess.Popen([sys.executable,'-m','testbed.extension2.study','run'],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
                status('resumed-sealed-transient-failure',collector_pid=child.pid,cell_id=last['cell_id'],log=str(current_log.relative_to(ROOT)))
                while child.poll() is None:
                    time.sleep(30);status('watching-resumed-collector',collector_pid=child.pid)


if __name__=='__main__':main()
