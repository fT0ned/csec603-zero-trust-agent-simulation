"""Deterministic tracked-source and study002-only evidence archive."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import zipfile
from testbed.common import ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    files=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    selected=[]
    for name in filter(None,files):
        if name.startswith('results/') and not name.startswith(('results/extension-study-002/','results/extension-study-002-pilot/')):continue
        if Path(name).name=='.env' or name.startswith(('.runtime/','.venv/','.git/')):raise ValueError('Forbidden archive path')
        selected.append(name)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name in sorted(selected):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            archive.writestr(info,(ROOT/name).read_bytes())
    sha=hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_name('SHA256SUMS').write_text(sha+'  '+args.output.name+'\n',encoding='ascii')
    print({'archive':str(args.output),'files':len(selected),'bytes':args.output.stat().st_size,'sha256':sha})


if __name__=='__main__':main()
