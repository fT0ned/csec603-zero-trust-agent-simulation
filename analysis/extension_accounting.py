"""Final descriptive ledger, runtime and semantic-intent evidence reconciliation."""
from collections import Counter, defaultdict
import csv
from decimal import Decimal
import json
from pathlib import Path
import sqlite3

from testbed.common import ROOT, write_json
from testbed.extension.analyse import read_runs
from testbed.intent_normalization import intent_key


def main():
    snapshot=ROOT/'results/extension-study-001/analysis/ledger-public.csv'
    if snapshot.exists():
        with snapshot.open(encoding='utf-8',newline='') as stream:
            entries=[{'id':int(r['id']),'reserved':float(r['reserved']),'actual':float(r['actual']) if r['actual'] else None,'state':r['state']} for r in csv.DictReader(stream)]
    else:
        ledger = sqlite3.connect(ROOT / '.runtime/spend.sqlite')
        entries = [dict(zip(('id','reserved','actual','state'), row)) for row in ledger.execute('SELECT * FROM spend ORDER BY id')]
        snapshot.parent.mkdir(exist_ok=True)
        with snapshot.open('w',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=('id','reserved','actual','state'))
            writer.writeheader()
            writer.writerows(entries)
    baseline_id = 16085
    pilot_last = json.loads((ROOT/'results/extension-study-pilot-001/ledger-accounting.json').read_text(encoding='utf-8'))['last_id']
    money = lambda value: Decimal(str(value or 0))
    charged = lambda row: money(row['actual'] if row['state']=='settled' else row['reserved'])
    accounting = {'baseline_id':baseline_id, 'baseline_cost_usd':float(sum((charged(e) for e in entries if e['id']<=baseline_id),Decimal(0))),
                  'ledger_total_usd':float(sum(map(charged,entries),Decimal(0))), 'budget_usd':25, 'phases':{}}
    observed_duplicates = []
    for phase, lower, upper in [('pilot',baseline_id,pilot_last),('full',pilot_last,max(e['id'] for e in entries))]:
        root=ROOT/('results/extension-study-pilot-001' if phase=='pilot' else 'results/extension-study-001')
        raw, primary=read_runs(root)
        reservations={}
        returned=Counter()
        fingerprints=Counter()
        http_status=Counter()
        for path in root.glob('runs/*/transcript.json'):
            for record in json.loads(path.read_text(encoding='utf-8')):
                if 'reservation_id' in record:
                    reservations[record['reservation_id']]=record
                response=record.get('response',{})
                if response.get('model'):
                    returned[response['model']]+=1
                if response.get('system_fingerprint'):
                    fingerprints[response['system_fingerprint']]+=1
                if record.get('http_status'):
                    http_status[str(record['http_status'])]+=1
        group=[e for e in entries if lower<e['id']<=upper]
        times=[r['started_at'] for r in raw if r.get('started_at')]
        ends=[r['finished_at'] for r in raw if r.get('finished_at')]
        accounting['phases'][phase]={'first_ledger_id':lower+1,'last_ledger_id':upper,'ledger_entries':len(group),
            'conservative_usd':float(sum(map(charged,group),Decimal(0))),
            'settled_usd':float(sum((money(e['actual']) for e in group if e['state']=='settled'),Decimal(0))),
            'retained_positive_reservation_usd':float(sum((money(e['reserved']) for e in group if e['state']!='settled'),Decimal(0))),
            'uncertain_reservations':sum(e['state']!='settled' and e['reserved']>0 for e in group),
            'zero_cost_unsettled_local_reservations':sum(e['state']!='settled' and e['reserved']==0 for e in group),
            'unattributed_entries':[e for e in group if e['id'] not in reservations],
            'transcript_response_cost_usd':float(sum((money(r.get('cost_usd')) for r in reservations.values()),Decimal(0))),
            'returned_models':dict(returned),'returned_fingerprints':dict(fingerprints),'http_error_statuses':dict(http_status),
            'raw':len(raw),'primary':len(primary),'first_started_at':min(times),'last_finished_at':max(ends),
            'wall_span_seconds':max(ends)-min(times),
            'known_raw_run_seconds':sum(r.get('runtime_seconds') or 0 for r in raw),
            'raw_missing_runtime':sum(r.get('runtime_seconds') is None for r in raw)}
        for row in primary:
            path=Path(row['_folder'])/'actions.json'
            groups=defaultdict(list)
            if not path.exists():
                continue
            for action in json.loads(path.read_text(encoding='utf-8')):
                call=action['request']
                if call['action']=='payments.pay' and action['data']['outcome']=='executed':
                    groups[intent_key({'action':call['action'],'params':call['params']})].append(call)
            for key, calls in groups.items():
                if len(calls)>1:
                    observed_duplicates.append({'phase':phase,'cell_id':row['cell_id'],'semantic_intent':json.loads(key),'executed':len(calls)})
    accounting['extension_conservative_usd']=sum(p['conservative_usd'] for p in accounting['phases'].values())
    accounting['note']='Token-rate/ceiling accounting, not provider invoice reconciliation. Unattributed responses remain missing; local electricity is unmeasured.'
    write_json(ROOT/'results/extension-study-001/analysis/accounting.json',accounting)
    write_json(ROOT/'docs/extension-intent-observation-scan.json',{'scope':'Final primary pilot and full action artifacts; semantic duplicate payments are a diagnostic, not additional experimental units.',
        'suspected_duplicate_payment_groups':observed_duplicates,'universal_invariant':'Refuted by docs/extension-intent-edge-case.json regardless of observed registered cells.'})
    print(json.dumps({k:accounting[k] for k in ('ledger_total_usd','extension_conservative_usd')}))


if __name__=='__main__':
    main()
