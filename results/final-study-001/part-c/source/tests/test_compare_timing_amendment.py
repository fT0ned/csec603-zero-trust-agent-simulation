"""Temporary synthetic software fixtures only; never replacement study results."""
import copy
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HELPER=Path(__file__).resolve().parents[1]/'scripts/compare_timing_amendment.py'
spec=importlib.util.spec_from_file_location('compare_timing_amendment',HELPER)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class TimingComparisonTests(unittest.TestCase):
    def contrast(self,**extra):
        return dict(collection_id='old',mode='llm',phase='full',model='model',model_snapshot='snapshot',
                    scenario='S4',ttl_seconds=300,revocation_mode='now-vs-expiry',approval_dependent=False,
                    condition='C2',left='C2:now',right='C2:expiry',metric='revocation_to_denial_ms',
                    effect={'estimate':None,'ci_low':None,'ci_high':None},n_left=30,n_right=30,
                    p_value=None,p_holm=None,method='Not measured',**extra)

    def test_full_outer_join_all_strata_and_condition(self):
        before=self.contrast();after=copy.deepcopy(before)
        after.update(collection_id='new',source_path='new-source')
        after['effect']={'estimate':42,'ci_low':1,'ci_high':80};after['p_value']=.01;after['p_holm']=.1
        distinct=copy.deepcopy(after);distinct.update(condition='C1',left='C1:now',right='C1:expiry')
        rows=module.join_rows([before],[after,distinct])
        self.assertEqual(len(rows),2)
        matched=next(r for r in rows if r['match_status']=='matched')
        self.assertIsNone(matched['original']['effect']['estimate'])
        self.assertEqual(matched['amended']['effect']['estimate'],42)
        self.assertEqual(sum(r['match_status']=='missing_original' for r in rows),1)
        changed=copy.deepcopy(after);changed['approval_dependent']=True
        self.assertEqual({r['match_status'] for r in module.join_rows([before],[changed])},{'missing_original','missing_amended'})
        with self.assertRaises(ValueError):module.join_rows([before,before],[after])

    def test_real_files_required_before_output_and_preserved_judgments(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);original=root/'old/report.json';amended=root/'new/report.json';output=root/'presentation'
            original.parent.mkdir();amended.parent.mkdir()
            h={'hypotheses':[{'collection_id':'old','hypothesis':'H1b','judgment':'Supported raw analyzer label'}],
               'contrasts':[],'sanity_checks':[],'eligibility':{'eligible':True}}
            before={'comparisons':[self.contrast()],'hypothesis_assessment':h}
            original.write_text(json.dumps(before),encoding='utf-8')
            with self.assertRaises(FileNotFoundError):module.compare(original,amended,output)
            self.assertFalse(output.exists())
            after=copy.deepcopy(before);after['comparisons'][0]['collection_id']='new'
            after['hypothesis_assessment']['hypotheses'][0]['collection_id']='new'
            amended.write_text(json.dumps(after),encoding='utf-8')
            old_bytes=original.read_bytes();new_bytes=amended.read_bytes()
            result=module.compare(original,amended,output)
            self.assertEqual(result['counts']['contrasts']['matched'],1)
            row=result['sections']['hypothesis-summary'][0]
            self.assertEqual(row['original']['judgment'],'Supported raw analyzer label')
            self.assertIn('quality veto',row['original_quality_label'])
            self.assertIn('conditional',row['amended_quality_label'])
            self.assertFalse(result['quality_acceptance_inferred'])
            with (output/'contrasts.csv').open(encoding='utf-8') as stream:
                csv_rows=list(csv.DictReader(stream))
            self.assertIn('original.effect.ci_low',csv_rows[0])
            self.assertEqual(csv_rows[0]['original.effect.estimate'],'')
            self.assertEqual(original.read_bytes(),old_bytes);self.assertEqual(amended.read_bytes(),new_bytes)

if __name__=='__main__':unittest.main()
