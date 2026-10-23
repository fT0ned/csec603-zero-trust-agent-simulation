"""Preserve a read-only provider balance and shared-ledger reconciliation snapshot."""
import argparse
from contextlib import closing
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sqlite3
import httpx
from testbed.common import ROOT

def snapshot():
    key=os.environ.get('DEEPSEEK_API_KEY')
    if not key:raise ValueError('DEEPSEEK_API_KEY missing')
    with httpx.Client(timeout=30,trust_env=False) as client:
        response=client.get('https://api.deepseek.com/user/balance',headers={'Authorization':'Bearer '+key})
        if response.status_code!=200:raise RuntimeError('Provider balance HTTP '+str(response.status_code))
        data=response.json()
    safe={'is_available':data.get('is_available'),'balance_infos':[
        {k:row.get(k) for k in ['currency','total_balance','granted_balance','topped_up_balance']}
        for row in data.get('balance_infos',[])]}
    ledger=ROOT/'.runtime/spend.sqlite';summary=[]
    if ledger.exists():
        with closing(sqlite3.connect(ledger)) as db:
            summary=[{'state':state,'requests':count,'reserved_usd':reserved,'actual_usd':actual,'charged_or_reserved_usd':used}
              for state,count,reserved,actual,used in db.execute('SELECT state,count(*),sum(reserved),sum(actual),sum(coalesce(actual,reserved)) FROM spend GROUP BY state')]
    return {'created_at':datetime.now(timezone.utc).isoformat(),'provider':'deepseek','endpoint':'https://api.deepseek.com/user/balance',
            'provider_balance':safe,'shared_ledger':summary,'established_total_cap_usd':float(os.environ.get('STUDY_BUDGET_USD',0)),
            'note':'Read-only account snapshot. Balance can be rounded and reflect other activity; a difference is not an exact per-batch invoice. Ledger preserves uncertain requests at their reserved upper bound.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();result=snapshot();args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':main()
