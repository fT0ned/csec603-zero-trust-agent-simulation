"""Seal registered pilot raw evidence and all study002 decision/analysis sources."""
import hashlib
import time

from testbed.common import ROOT,digest,write_json
from testbed.extension2.study import CONFIG,FREEZE,TAG,PILOT,read,selection,cells,source_files,lf_hash,verify_protected


def main():
    config=read(CONFIG)
    chosen=selection(PILOT)
    if chosen['carried_strata']!=config['carried_strata']:raise ValueError('apply registered pilot selection first')
    verify_protected(full=True)
    extra=['analysis/study002.py','scripts/freeze_extension2.py','scripts/setup_extension2.ps1','scripts/prepare_extension_fonts.py',
           'scripts/prepare_extension2_profiles.py','docs/extension-study-002-runtime-profiles.json','docs/extension-study-002-amendments.md']
    source=sorted(set(source_files()+extra))
    raw=[p for p in PILOT.rglob('*') if p.is_file() and 'analysis' not in p.relative_to(PILOT).parts and p.name!='completion-status.json']
    frozen={'tag':TAG,'frozen_at':time.time(),'config_sha256':digest(config),'file_hashes':{p:lf_hash(p) for p in source},
            'pilot_hashes':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(raw)},
            'full_units':len(cells(config)),'paired_comparisons':3*sum(s['family']!='benign' for s in config['carried_strata']),
            'derivation':'Raw pilot seals and selection frozen; derived pilot analysis may be regenerated. No payload/prompt/model/rule changes after pilot.'}
    write_json(FREEZE,frozen)
    print({k:frozen[k] for k in ('tag','config_sha256','full_units','paired_comparisons')})


if __name__=='__main__':main()
