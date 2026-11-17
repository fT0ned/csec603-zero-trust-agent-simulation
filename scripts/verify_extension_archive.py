"""Inspect every decompressed release member for known secrets and private paths."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

from dotenv import dotenv_values
from testbed.common import ROOT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    args=parser.parse_args()
    secrets=[]
    for filename in (ROOT/'.env',ROOT/'.runtime/control.env'):
        if filename.exists():
            secrets.extend(value.encode() for key,value in dotenv_values(filename).items() if value and len(value)>=12 and any(word in key.upper() for word in ('SECRET','KEY','TOKEN')))
    violations=[]
    checked=0
    with zipfile.ZipFile(args.archive) as archive:
        for item in archive.infolist():
            path=PurePosixPath(item.filename)
            forbidden=(path.is_absolute() or '..' in path.parts or path.name=='.env' or 'APIKEY' in path.name.upper()
                       or any(part in ('.runtime','.venv','.git','.secrets','credentials','secrets') for part in path.parts)
                       or path.suffix in ('.pem','.key','.p12','.pfx','.jwt'))
            content=archive.read(item)
            key_material=re.search(rb'-----BEGIN (?:EC |RSA )?PRIVATE KEY-----\r?\n[A-Za-z0-9+/=]{40}',content)
            if forbidden or key_material or any(secret in content for secret in secrets):
                violations.append(item.filename)
            checked+=1
    report={'passed':not violations,'members_checked':checked,'known_secret_values_checked':len(secrets),'violating_paths':violations,
            'archive_sha256':hashlib.sha256(args.archive.read_bytes()).hexdigest(),
            'scope':'Every decompressed member; exact known secret values/private path/key material scan, not a general entropy or history audit.'}
    print(json.dumps(report))
    raise SystemExit(0 if not violations else 2)


if __name__=='__main__':
    main()
