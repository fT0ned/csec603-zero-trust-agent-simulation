import copy
import json

from testbed.common import ROOT
from testbed.extension2.fixtures import fixture,FAMILIES,MODELS
from testbed.extension2.scoring import violations
from testbed.extension2.security import Issuer,actor_path
from testbed.extension2.study import cells


def test_all_attack_targets_are_synthetic_and_outside_task_but_good_calls_are_valid():
    for family in FAMILIES:
        for index in range(30):
            f=fixture(family,221000+index,index)
            assert not violations(f['good'],f['delegation'],[])
            assert violations(f['bad'],f['delegation'],[])
            assert bool(f['malicious_edges'])==(family!='benign')
            assert f['good']['action'] in f['content']


def test_full_manifest_is_fixed_balanced_and_fresh():
    cfg=json.loads((ROOT/'configs/extension-study-002.json').read_text(encoding='utf-8'))
    cfg['carried_strata']=[{'model':MODELS[0],'prompt':'neutral-v1','family':'bec'}]
    main=cells(cfg);pilot=cells(cfg,True)
    assert len(pilot)==240 and len(main)==120+20+240
    assert len({r['cell_id'] for r in main})==len(main)
    assert not {r['seed'] for r in main}&{r['seed'] for r in pilot}
    assert len([r for r in main if r['experiment']=='E5' and r['condition']=='C-PAA-002'])==30


def test_strict_scope_and_budget_chains_are_distinguished():
    issuer=Issuer();root=issuer.root('task','human',['read','export','pay'],{'records':10,'payment':10},'A')
    a=issuer.exchange(root,'A',['read','export'],{'records':5,'payment':5},'B')
    b=issuer.exchange(a,'B',['read'],{'records':2,'payment':2},'')
    assert issuer.verify(b)['scope']==['read'] and actor_path(issuer.verify(b))==['human','A','B']
    isolated=issuer.exchange(a,'B',['read','export'],{'records':2,'payment':2},'')
    assert issuer.verify(isolated)['budget']['records']==2
