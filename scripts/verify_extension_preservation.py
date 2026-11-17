"""Verify protected original bytes, extension freeze and final test evidence."""
import hashlib
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET

from testbed.common import ROOT, write_json


def main():
    private=ROOT/'.runtime/extension-original-manifest.json'
    public=ROOT/'docs/extension-original-file-manifest.json'
    inventory=private if private.exists() else public
    expected=json.loads(inventory.read_text(encoding='utf-8'))
    mismatches=[name for name,sha in expected.items() if not (ROOT/name).is_file() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha]
    freeze=json.loads((ROOT/'configs/extension-study-freeze.json').read_text(encoding='utf-8'))
    frozen_mismatches=[name for name,sha in freeze['file_hashes'].items() if hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=sha]
    pilot_mismatches=[name for name,sha in freeze['pilot_file_hashes'].items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha]
    xml=ET.parse(ROOT/'docs/verification/extension-final-tests.xml').getroot()
    suites=[xml] if xml.tag=='testsuite' else list(xml)
    tests=sum(int(s.attrib.get('tests',0)) for s in suites)
    failures=sum(int(s.attrib.get(k,0)) for s in suites for k in ('failures','errors'))
    skipped=sum(int(s.attrib.get('skipped',0)) for s in suites)
    passed=not(mismatches or frozen_mismatches or pilot_mismatches or failures)
    if private.exists() and not mismatches:
        public.write_bytes(private.read_bytes())
    report={'checked_at':time.time(),'passed':passed,'tests_passed':tests-failures-skipped,'tests_failed_or_errored':failures,'tests_skipped':skipped,
            'original_files_checked':len(expected),'original_mismatches':mismatches,'extension_frozen_files_checked':len(freeze['file_hashes']),
            'extension_source_mismatches':frozen_mismatches,'frozen_pilot_files_checked':len(freeze['pilot_file_hashes']),
            'frozen_pilot_mismatches':pilot_mismatches,'inventory_sha256':hashlib.sha256(inventory.read_bytes()).hexdigest()}
    write_json(ROOT/'docs/extension-final-validation.json',report)
    previous=json.loads((ROOT/'docs/extension-original-preservation.json').read_text(encoding='utf-8'))
    write_json(ROOT/'docs/extension-original-preservation.json',{'checked_at':report['checked_at'],'previous_verification_at':previous['checked_at'],
        'file_count':len(expected),'mismatches':mismatches,'passed':not mismatches,'inventory_sha256':report['inventory_sha256'],
        'scope':'Every protected original final-study-001 file and frozen source; raw byte SHA256 against initial inventory, now archived in docs/extension-original-file-manifest.json.'})
    print(json.dumps(report))
    raise SystemExit(0 if passed else 1)


if __name__=='__main__':
    main()
