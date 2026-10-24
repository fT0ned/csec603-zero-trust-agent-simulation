import json
import unittest
from testbed.common import digest, validate_action
from testbed.audit import verify,tamper_suite,attribution
from testbed.fixtures import fixture
from testbed.runner import manifest,validate_config

class Controls(unittest.TestCase):
    def test_manifest_has_no_duplicate_sweep_cells(self):
        config=json.load(open('configs/study.json'))
        cells=manifest(config)
        self.assertEqual(len(cells),1200)
        self.assertEqual(len({json.dumps(x,sort_keys=True) for x in cells}),1200)
        self.assertEqual(sum(x['scenario']=='S4' for x in cells),540)
        self.assertTrue(all(x['scenario'] in ['S2','S5'] for x in cells if x['condition'] in ['C2-RS','C2-noWF']))

    def test_tamper_tail_is_detected(self):
        rows=[]
        for i in range(3):
            row={'sequence':i+1,'result':'executed','previous_hash':rows[-1]['hash'] if rows else '0'*64}
            row['hash']=digest(row);rows.append(row)
        cp={'count':3,'hash':rows[-1]['hash']}
        self.assertTrue(verify(rows,cp)['valid'])
        self.assertTrue(all(not x['valid'] for x in tamper_suite(rows,cp).values()))

    def test_no_truth_leakage_attribution(self):
        self.assertEqual(attribution([{'input_provenance':['external']}]),'none')
        self.assertEqual(attribution([{'parameter_provenance':[{'parameter':'to'}]}]),'coercion')
        self.assertEqual(attribution([{'origin':'attacker','expected_origin':'agent'}]),'impersonation')

    def test_fixed_scope_and_workflow_intent(self):
        for seed in range(4):
            f=fixture('S5',seed)
            if f['payload']['id']=='chunked-export':
                self.assertEqual(sum(x['params'].get('limit',0) for x in f['task']['expected']),f['delegation']['max_records'])
                self.assertNotIn('payments.pay',f['delegation']['actions'])
        for scenario in ['S1','S2','S3','S4','S5']:
            for seed in range(4):
                f=fixture(scenario,seed)
                for call in f['task']['expected']:
                    validate_action(call['action'],call['params'])
                    self.assertIn(call['action'],f['delegation']['actions'])

    def test_schema_rejects_forged_authority_and_bad_numbers(self):
        for params in [{'offset':0,'limit':True},{'offset':0,'limit':-1},{'offset':0,'limit':5,'principal':'admin'}]:
            with self.assertRaises(ValueError): validate_action('crm.export',params)
        with self.assertRaises(ValueError): validate_action('payments.pay',{'vendor':'vendor-1','amount':float('nan'),'invoice':'a'})

    def test_full_gate_blocks_unfrozen_study(self):
        config=json.load(open('configs/study.json'));config['mode']='scripted'
        with self.assertRaises(ValueError): validate_config(config)

if __name__=='__main__':unittest.main()
