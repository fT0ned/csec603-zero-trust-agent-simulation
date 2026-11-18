"""Sanitized host/software and descriptive Docker resource summaries."""
from collections import defaultdict
import importlib.metadata
import json
import platform
import re
import subprocess
import sys
import time
from analysis.statistics import describe
from testbed.common import ROOT,write_json
from testbed.extension.analyse import table,latex_table,continuous_text


def run(command):return subprocess.check_output(command,cwd=ROOT,text=True,encoding='utf-8',timeout=60).strip()


def mib(text):
    match=re.fullmatch(r'\s*([\d.]+)\s*([A-Za-z]+)\s*',text)
    if not match:raise ValueError('Unknown memory unit')
    amount=float(match[1]);units={'B':1/1048576,'KiB':1/1024,'MiB':1,'GiB':1024,'TiB':1048576,'kB':1000/1048576,'MB':1e6/1048576,'GB':1e9/1048576}
    return amount*units[match[2]]


def main():
    services=defaultdict(lambda:{'cpu_percent':[],'memory_MiB':[]});frames=errors=0
    for phase in ('extension-study-002-pilot','extension-study-002'):
        path=ROOT/'results'/phase/'resources.jsonl'
        if not path.exists():continue
        for line in path.read_text(encoding='utf-8').splitlines():
            row=json.loads(line);frames+=1
            errors+=bool(row.get('observer_error') or row.get('exit_code',0)!=0)
            for sample in row.get('samples',[]):
                target=services[(phase,sample['Name'])]
                try:target['cpu_percent'].append(float(sample['CPUPerc'].removesuffix('%')))
                except (KeyError,ValueError):pass
                try:target['memory_MiB'].append(mib(sample['MemUsage'].split('/')[0]))
                except (KeyError,ValueError):pass
    summaries=[{'phase':phase,'container':name,**{k:describe(v) for k,v in values.items()}} for (phase,name),values in sorted(services.items())]
    docker=json.loads(run(['docker','info','--format','{"server_version":"{{.ServerVersion}}","logical_cpus":{{.NCPU}},"memory_bytes":{{.MemTotal}}}']))
    gpu=run(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'])
    memory=run(['powershell','-NoProfile','-NonInteractive','-Command','(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory'])
    versions={name:importlib.metadata.version(name) for name in ('pytest','fastapi','httpx','PyJWT','matplotlib','fonttools')}
    write_json(ROOT/'docs/extension-study-002-host-resources.json',{'checked_at':time.time(),'platform':platform.platform(),
        'windows_version':platform.win32_ver(),'python':sys.version,'logical_cpus':__import__('os').cpu_count(),
        'physical_memory_bytes':int(memory),'docker':docker,'gpu_csv':gpu,'packages':versions,
        'resource_frames':frames,'observer_error_frames':errors,'resource_summaries':summaries,
        'interpretation':'Descriptive repeated container observations, not independent trials, whole-host power or enterprise capacity. Docker CPU100%=one logical CPU; memory uses MiB.'})
    out=ROOT/'results/extension-study-002/publication';out.mkdir(exist_ok=True)
    headers=['Phase','Container','CPU%, frames; median(IQR)','Memory MiB, frames; median(IQR)']
    rows=[[s['phase'],s['container'],str(s['cpu_percent']['n'])+'; '+continuous_text(s['cpu_percent']),str(s['memory_MiB']['n'])+'; '+continuous_text(s['memory_MiB'])] for s in summaries]
    (out/'resources.md').write_text(table(headers,rows),encoding='utf-8');(out/'resources.tex').write_text(latex_table(headers,rows),encoding='utf-8')
    print(json.dumps({'host_record':'docs/extension-study-002-host-resources.json','resource_frames':frames,'observer_error_frames':errors}))


if __name__=='__main__':main()
