"""Offline gate fixtures; never collect, accept or build an actual view."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[1]/'results/timing-sensitivity-001/build_referenced_view.py'
spec=importlib.util.spec_from_file_location('sensitivity_builder',SCRIPT)
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

class SensitivityGateTests(unittest.TestCase):
    def test_deployed_crlf_git_lf_contract_and_real_change_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);original=root/'deployed.py';snapshot=root/'git.py'
            original.write_bytes(b'def f():\r\n    return 1\r\n')
            snapshot.write_bytes(b'def f():\n    return 1\n')
            old_bytes=original.read_bytes();git_bytes=snapshot.read_bytes()
            captured=builder.sha(original);tagged=builder.sha(snapshot)
            self.assertNotEqual(captured,tagged)
            builder.verify_control_snapshot(original,snapshot,captured,tagged)
            self.assertEqual(original.read_bytes(),old_bytes);self.assertEqual(snapshot.read_bytes(),git_bytes)
            # Even a newly hashed code mutation cannot satisfy text equivalence.
            snapshot.write_bytes(b'def f():\n    return 2\n')
            with self.assertRaisesRegex(ValueError,'text differs'):
                builder.verify_control_snapshot(original,snapshot,captured,builder.sha(snapshot))
            # Unapproved newline-only changes after the tagged snapshot still fail.
            snapshot.write_bytes(old_bytes)
            with self.assertRaisesRegex(ValueError,'tagged source manifest'):
                builder.verify_control_snapshot(original,snapshot,captured,tagged)

    def test_acceptance_binds_each_replacement_and_postdates_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'run';folder.mkdir()
            (folder/'summary.json').write_text(json.dumps({'metadata':{'finished_at':100}}))
            row={'source_collection':'test','source_run_id':'r1','original_run_id':'old','summary_sha256':'s','raw_manifest_sha256':'m','source_folder':'run','is_replacement':True}
            unit={k:row[k] for k in ['source_collection','source_run_id','original_run_id','summary_sha256','raw_manifest_sha256']}
            review={'selected_replacement_units':[unit],'reviewed_at':'1970-01-01T00:02:00+00:00'}
            with patch.object(builder,'MAIN',root):
                builder.verify_unit_review(review,[row])
                with self.assertRaises(ValueError):builder.verify_unit_review({**review,'selected_replacement_units':[]},[row])
                with self.assertRaises(ValueError):builder.verify_unit_review({**review,'reviewed_at':'1970-01-01T00:01:00+00:00'},[row])
                changed={**unit,'summary_sha256':'changed'}
                with self.assertRaises(ValueError):builder.verify_unit_review({**review,'selected_replacement_units':[changed]},[row])

    def test_all_selected_seals_checked_and_escaping_paths_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'run';folder.mkdir();data=folder/'summary.json';data.write_text('{}')
            manifest=folder/'raw-manifest.json'
            manifest.write_text(json.dumps({'hash_scheme':'sha256-bytes','files':{'summary.json':builder.sha(data)}}))
            row={'source_folder':'run','source_run_id':'r1'}
            with patch.object(builder,'MAIN',root):
                self.assertTrue(builder.verify_selected_raw([row])['valid'])
                data.write_text('{"changed":true}')
                self.assertFalse(builder.verify_selected_raw([row])['valid'])
                manifest.write_text(json.dumps({'hash_scheme':'sha256-bytes','files':{'../escape':'hash'}}))
                with self.assertRaises(ValueError):builder.verify_selected_raw([row])

    def test_prospective_tag_identity_must_be_immutable(self):
        for changed in ['wrong-commit','c31ef598'+'0'*32]:
            with self.subTest(commit=changed),patch.object(builder.subprocess,'check_output',return_value=changed):
                with self.assertRaisesRegex(ValueError,'tag identity'):builder.verify_predata()

if __name__=='__main__':unittest.main()
