"""Verify export checksums, original raw seals, source and figure hashes offline.

No extraction, provider calls, raw changes or scientific acceptance. A valid ZIP
can contain a quality-vetoed study. --scan-local-secrets checks known local keys
without printing them; it is not a general secret-scanning service.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


def verify(path, secrets=()):
    errors=[];secret_members=set();hashes={};sealed=0;figures=0;sources=0
    secrets=[s for s in secrets if len(s)>=12]
    overlap=max([1]+[len(s) for s in secrets])-1
    def safe(name):
        p=PurePosixPath(name)
        return not p.is_absolute() and '..' not in p.parts and '\\' not in name and ':' not in name
    def scan(stream, name):
        h=hashlib.sha256();tail=b''
        while block:=stream.read(1024*1024):
            h.update(block)
            if any(s in tail+block for s in secrets):secret_members.add(name)
            tail=(tail+block)[-overlap:] if overlap else b''
        return h.hexdigest()
    with zipfile.ZipFile(path) as archive:
        names=archive.namelist();members=set(names)
        if len(names)!=len(members):errors.append('Duplicate ZIP member names')
        if any(not safe(name) for name in names):raise ValueError('Unsafe ZIP member path')
        sums=json.loads(archive.read('SHA256SUMS.json'))
        for name in names:
            if any(secret in name.encode('utf-8') for secret in secrets):secret_members.add(name)
            if archive.getinfo(name).is_dir():continue
            if name not in sums and name not in {'SHA256SUMS.json','BUNDLE_README.txt'}:
                errors.append('ZIP member absent from export checksum manifest: '+name)
            with archive.open(name) as stream:hashes[name]=scan(stream,name)
            if name.endswith('.jsonl.gz') and secrets:
                with archive.open(name) as compressed, gzip.GzipFile(fileobj=compressed) as decoded:scan(decoded,name)
        for name,expected in sums.items():
            if name not in members:errors.append('Checksum member missing: '+name)
            elif hashes.get(name)!=expected:errors.append('Export checksum mismatch: '+name)
        def check(name, expected, kind):
            if name not in members:errors.append(kind+' missing: '+name)
            elif name not in sums:errors.append(kind+' absent from export checksum manifest: '+name)
            elif hashes[name]!=expected:errors.append(kind+' original hash mismatch: '+name)
        for name in names:
            if name.startswith('results/runs/') and name.endswith('/raw-manifest.json'):
                manifest=json.loads(archive.read(name));prefix=name.rsplit('/',1)[0]+'/'
                if manifest.get('hash_scheme')!='sha256-bytes':errors.append('Unsupported raw seal: '+name);continue
                for relative,expected in manifest['files'].items():
                    sealed+=1;check(prefix+relative.replace('\\','/'),expected,'Raw seal')
            elif name.startswith('results/') and name.endswith('/figure-manifest.json'):
                prefix=name.rsplit('/',1)[0]+'/'
                for relative,expected in json.loads(archive.read(name))['exports'].items():
                    figures+=1;check(prefix+relative,expected,'Generated figure/table')
        if 'results/manifest.json' in members:
            for relative,expected in json.loads(archive.read('results/manifest.json')).get('source_sha256',{}).items():
                sources+=1;check('source/'+relative.replace('\\','/'),expected,'Collection source')
        if secret_members:errors.append('Known local secret found in exported member bytes')
        provenance=json.loads(archive.read('EXPORT_PROVENANCE.json')) if 'EXPORT_PROVENANCE.json' in members else None
    result={'integrity_passed':not errors,'errors':errors,'export_checksums_checked':len(sums),'all_file_members_hashed_and_scanned':len(hashes),
        'original_raw_members_checked':sealed,'source_files_checked':sources,'figure_table_exports_checked':figures,
        'known_local_secrets_checked':len(secrets),'secret_member_paths':sorted(secret_members),
        'batch_quality':provenance.get('batch_quality') if provenance else None,
        'scientific_acceptance_inferred':False,'archive':str(Path(path).resolve())}
    # Even an adversarial member name or embedded quality record must not echo a
    # known private value into diagnostics. Source bytes are never changed.
    def scrub(value):
        if isinstance(value,str):
            for secret in secrets:
                text=secret.decode('utf-8',errors='ignore')
                if text:value=value.replace(text,'[REDACTED]')
            return value
        if isinstance(value,list):return [scrub(item) for item in value]
        if isinstance(value,dict):return {scrub(key):scrub(item) for key,item in value.items()}
        return value
    return scrub(result)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('archive',type=Path)
    parser.add_argument('--output',type=Path);parser.add_argument('--scan-local-secrets',action='store_true')
    args=parser.parse_args();secrets=[]
    if args.scan_local_secrets:
        from dotenv import dotenv_values
        root=Path(__file__).resolve().parents[1]
        for file in [root/'.env',root/'.runtime/control.env']:
            secrets.extend(str(v).encode() for k,v in dotenv_values(file).items() if v and any(s in k.upper() for s in ['API_KEY','SECRET','PASSWORD']))
    result=verify(args.archive,secrets)
    if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='batch_quality'}))
    raise SystemExit(0 if result['integrity_passed'] else 2)


if __name__=='__main__':main()
