"""Run a separately sealed enforcement-extension collection; never pool originals."""
import argparse
import json
import subprocess
from pathlib import Path
from testbed.common import ROOT, digest, write_json
from testbed.runner import run_batch, config_fingerprint
from testbed.power import keep_awake

def check_seal(name):
    seal = json.loads((ROOT/'configs/enforcement-freeze.json').read_text())
    if seal.get('status') != 'approved': raise ValueError('Extension protocol is not frozen')
    tag = seal['tag']
    tagged = subprocess.check_output(['git','show',tag+':configs/enforcement-freeze.json'],cwd=ROOT,text=True)
    if json.loads(tagged) != seal: raise ValueError('Extension freeze differs from tag')
    local = subprocess.check_output(['git','rev-parse',tag],cwd=ROOT,text=True).strip()
    remote = subprocess.check_output(['git','ls-remote','origin','refs/tags/'+tag],cwd=ROOT,text=True).split()
    if not remote or remote[0] != local: raise ValueError('Push extension freeze tag first')
    for relative, expected in seal['file_hashes'].items():
        if digest((ROOT/relative).read_text(encoding='utf-8')) != expected:
            raise ValueError('Extension source/protocol changed: '+relative)
    config = json.loads((ROOT/seal['studies'][name]['config']).read_text())
    if config_fingerprint(config) != seal['studies'][name]['config_sha256']:
        raise ValueError('Extension configuration changed')
    return seal, config

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study',choices=['neutral','stress'])
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    seal,config=check_seal(args.study)
    args.output.mkdir(parents=True,exist_ok=True)
    if (args.output/'manifest.json').exists(): raise ValueError('Use a fresh collection directory')
    write_json(args.output/'extension-freeze.json',seal)
    images=subprocess.check_output(['docker','compose','images','--format','json'],cwd=ROOT,text=True)
    (args.output/'runtime-images.json').write_text(images,encoding='utf-8')
    with keep_awake(): result=run_batch(config,args.output)
    return 0 if not result['failures'] else 2

if __name__=='__main__':raise SystemExit(main())
