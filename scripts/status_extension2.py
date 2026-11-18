"""Read-only operational status; no outcome-dependent sampling decisions."""
from pathlib import Path
import json
import sqlite3
import time
from testbed.common import ROOT


def main():
    folder=ROOT/'results/extension-study-002'
    progress=json.loads((folder/'progress.json').read_text()) if (folder/'progress.json').exists() else {}
    candidates=list((ROOT/'.runtime/extension2').glob('full*.log'))
    log=max(candidates,key=lambda p:p.stat().st_mtime) if candidates else ROOT/'.runtime/extension2/full.log'
    last=log.read_text(encoding='utf-8').splitlines()[-1:] if log.exists() else []
    try:unit=json.loads(last[0]) if last else {}
    except ValueError:unit={'log_tail':'non-JSON status; inspect private log'}
    with sqlite3.connect((ROOT/'.runtime/spend.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        charged=db.execute('SELECT coalesce(sum(coalesce(actual,reserved)),0) FROM spend').fetchone()[0]
    started=[]
    for monitor in folder.glob('clock-monitor-*.jsonl'):
        with monitor.open() as stream:
            line=stream.readline()
        if line:
            sample=json.loads(line)
            started.append(sample)
    print(json.dumps({'time':time.time(),**progress,'global_ledger_charged_usd':charged,
        'current_model':unit.get('model'),'current_experiment':unit.get('experiment'),
        'status':unit.get('status'),'clock_monitor_sessions':len(started)},separators=(',',':')))


if __name__=='__main__':main()
