"""Scripted pre-pilot integration assertions; never pooled with E5/E6 research."""
import argparse
from pathlib import Path
import time

from testbed.common import ROOT,write_json
from testbed.audit import verify
from .fixtures import fixture
from .harness import Actors,Session
from .scoring import score
from .study import run_one,read,CONFIG


def check(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);results=[]
    with Actors() as actors:
        for index in (0,1,2,3):
            for condition in ('C0-002','C2-002','C3-9449-002','C-PAA-002','C-PAA-B-002'):
                f=fixture('bec',991000+index,index);s=Session(actors,f,condition)
                try:
                    if condition!='C0-002':assert s.exchange()['ok']
                    read_value=s.invoke(f['read'],source='forced-read')
                    bad=s.invoke(f['bad']);good=s.invoke(f['good'])
                    evidence=s.evidence();measured=score(s.actions,evidence['independent'],f)
                    assert read_value['outcome']=='executed'
                    assert bad['allowed']==(condition=='C0-002')
                    assert good['allowed']
                    assert bad['audit']['classification']=='coercion'
                    assert measured['coerced_write'] and measured['committed_harm']==(condition=='C0-002')
                    assert verify(evidence['audit'],evidence['checkpoint'])['valid']
                    if condition.startswith('C-PAA'):assert bad['audit']['response_action']=='deny_keep_identity_flag_input'
                    results.append({'workload':f['workload'],'index':index,'condition':condition,'malicious_allowed':bad['allowed'],'good_allowed':good['allowed'],'classification':bad['audit']['classification']})
                finally:s.close()
        for case in ('B-within','B-scope','B-budget','A-budget'):
            for condition in ('C1-002','C3-9449-002'):
                row=run_one({'experiment':'E6','mode':'scripted','case':case,'condition':condition,'seed':992000,'index':0,
                             'cell_id':'engineering-'+case+'-'+condition},read(CONFIG),output,actors)
                assert row['status']=='completed' and row['correct_to_condition'] and row['chain_reconstructed'],row
                if condition=='C3-9449-002' and case=='B-scope':assert row['target_reason']=='capability_scope'
                if condition=='C3-9449-002' and case.endswith('budget'):assert row['target_reason']=='capability_budget'
                results.append({k:row[k] for k in ('case','condition','target_allowed','target_reason','chain_reconstructed')})
    write_json(output/'engineering-summary.json',{'passed':True,'cases':results,'evidence_class':'scripted engineering validation, not research sample','finished_at':time.time()})
    print({'engineering_cases':len(results),'passed':True})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'.runtime/extension2/engineering')
    check(parser.parse_args().output)
