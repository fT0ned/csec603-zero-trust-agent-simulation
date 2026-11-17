"""Build a small extension-only source/evidence archive from tracked files."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import zipfile

from testbed.common import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')
    selected = []
    for name in filter(None, names):
        if name.startswith('results/') and not name.startswith(('results/extension-study-001/', 'results/extension-study-pilot-001/')):
            continue
        base = Path(name).name
        if base == '.env' or 'APIKEY' in base.upper() or name.startswith(('.runtime/', '.venv/', '.git/')):
            raise RuntimeError('forbidden archive path: ' + name)
        selected.append(name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(selected):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, (ROOT / name).read_bytes())
    sha = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_name('SHA256SUMS').write_text(sha + '  ' + args.output.name + '\n', encoding='ascii')
    print({'archive': str(args.output), 'files': len(selected), 'bytes': args.output.stat().st_size, 'sha256': sha})


if __name__ == '__main__':
    main()
