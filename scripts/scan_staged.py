"""Scan staged bytes for known local secrets, including compressed evidence."""
import gzip
from pathlib import Path
import subprocess
from dotenv import dotenv_values
from testbed.common import ROOT

def main():
    secrets=[]
    for filename in [ROOT/'.env',ROOT/'.runtime/control.env']:
        if filename.is_file():
            secrets.extend(value.encode() for key,value in dotenv_values(filename).items()
                if value and len(value)>=12 and any(word in key.upper() for word in ['SECRET','KEY','TOKEN']))
    paths=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT).decode().split('\0')
    checked=0;violations=[]
    for path in filter(None,paths):
        forbidden=Path(path).name.startswith('APIKEY') or 'APIKEY' in Path(path).name or (Path(path).name=='.env') or path.startswith(('.runtime/','.venv/','.secrets/'))
        blob=subprocess.run(['git','show',':'+path],cwd=ROOT,capture_output=True)
        if blob.returncode:continue
        content=blob.stdout
        if path.endswith('.gz'):
            try:content=gzip.decompress(content)
            except OSError:pass
        checked+=1
        if forbidden or any(value in content for value in secrets):violations.append(path)
    print(__import__('json').dumps({'staged_files_checked':checked,'known_secret_values_checked':len(secrets),'violating_paths':violations,
       'passed':not violations,'scope':'Known local secret exact-byte scan, not a general secret-scanning service or history audit.'}))
    return 2 if violations else 0

if __name__=='__main__':raise SystemExit(main())
