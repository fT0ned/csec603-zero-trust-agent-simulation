"""Streaming audit verification and tamper checks; software fixtures only."""
import json
from pathlib import Path
import tempfile
import unittest

from testbed.audit import attribution,iter_audit_files,tamper_files,verify
from testbed.common import canonical,digest

class AuditStreamingTests(unittest.TestCase):
    def make_files(self,folder,count=100):
        # Crossing the 9/10 rotation boundary catches accidental lexical sorting.
        paths=[folder/'audit.jsonl']+[folder/f'audit.{i}.jsonl' for i in range(1,13)]
        previous='0'*64;rows=[]
        for sequence in range(1,count+1):
            row={'sequence':sequence,'request_id':str(sequence),'previous_hash':previous,'result':'executed'}
            row['hash']=digest(row);previous=row['hash'];rows.append(row)
        for i,path in enumerate(paths):
            selected=rows[i*8:(i+1)*8]
            path.write_text(''.join(canonical(row)+'\n' for row in selected),encoding='utf-8')
        return paths,{'count':count,'hash':previous}

    def test_valid_iterator_and_five_tamper_cases_across_rotations(self):
        with tempfile.TemporaryDirectory() as directory:
            paths,checkpoint=self.make_files(Path(directory))
            originals={p:p.read_bytes() for p in paths}
            result=verify(iter_audit_files(paths),checkpoint)
            self.assertTrue(result['valid']);self.assertEqual(result['count'],100)
            cases=tamper_files(paths,checkpoint)
            self.assertEqual(set(cases),{'alter','delete_middle','delete_tail','delete_all','reorder'})
            self.assertTrue(all(not case['valid'] for case in cases.values()))
            self.assertEqual(cases['delete_tail']['reason'],'checkpoint mismatch')
            self.assertEqual(cases['delete_tail']['count'],99)
            self.assertEqual(cases['delete_all']['count'],0)
            self.assertEqual(originals,{p:p.read_bytes() for p in paths})

    def test_final_chunk_deletion_detected_by_protected_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            paths,checkpoint=self.make_files(Path(directory))
            result=verify(iter_audit_files(paths[:-1]),checkpoint)
            self.assertFalse(result['valid']);self.assertEqual(result['reason'],'checkpoint mismatch')
            self.assertEqual(result['count'],96)

    def test_reordered_chunks_and_invalid_json_fail_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            paths,checkpoint=self.make_files(Path(directory))
            self.assertFalse(verify(iter_audit_files(sorted(paths)),checkpoint)['valid'])
            paths[-1].write_text('{malformed\n',encoding='utf-8')
            result=verify(iter_audit_files(paths),checkpoint)
            self.assertFalse(result['valid']);self.assertIn('unreadable audit',result['reason'])

    def test_single_pass_attribution_preserves_origin_priority_without_truth(self):
        rows=iter([{'parameter_provenance':[{'parameter':'invoice'}]},
                   {'origin':'attacker','expected_origin':'agent'}])
        self.assertEqual(attribution(rows),'impersonation')
        self.assertEqual(attribution(iter([{'input_provenance':['harmless'],'true_cause':'coercion'}])),'none')
        self.assertTrue(verify(iter(()),{'count':0,'hash':'0'*64})['valid'])

if __name__=='__main__':unittest.main()
