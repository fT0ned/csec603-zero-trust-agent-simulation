"""Publish the explicitly authorized extension release through existing Git credentials.

No credential is printed, stored, passed in arguments, or written to artifact files.
This is a publication helper, separate from the frozen experiment implementation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import httpx

from testbed.common import ROOT

REPOSITORY = 'fT0ned/csec603-zero-trust-agent-simulation'
TAG = 'extension-study-002'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--body-file', type=Path, required=True)
    parser.add_argument('--asset', type=Path, action='append', default=[])
    args = parser.parse_args()
    origin = subprocess.check_output(['git', 'remote', 'get-url', 'origin'], cwd=ROOT, text=True).strip()
    if origin != 'https://github.com/' + REPOSITORY + '.git':
        raise RuntimeError('unexpected publication remote')
    commit = subprocess.check_output(['git', 'rev-list', '-n', '1', TAG], cwd=ROOT, text=True).strip()
    process = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n',
                             text=True, capture_output=True, cwd=ROOT, timeout=120)
    credentials = dict(line.split('=', 1) for line in process.stdout.splitlines() if '=' in line)
    secret = credentials.get('password')
    if process.returncode or not secret:
        raise RuntimeError('existing Git credential unavailable; no credential output retained')
    headers = {'Authorization': 'Bearer ' + secret, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2026-03-10'}
    api = 'https://api.github.com/repos/' + REPOSITORY
    with httpx.Client(timeout=120, trust_env=False, headers=headers) as client:
        existing = client.get(api + '/releases/tags/' + TAG)
        if existing.status_code == 200:
            release = existing.json()
            if release['tag_name'] != TAG:
                raise RuntimeError('unexpected existing release')
        elif existing.status_code == 404:
            response = client.post(api + '/releases', json={'tag_name': TAG, 'target_commitish': commit,
                'name': 'PAA Extension Study 002', 'body': args.body_file.read_text(encoding='utf-8'),
                'draft': False, 'prerelease': False, 'make_latest': 'false'})
            if response.status_code != 201:
                raise RuntimeError('GitHub release creation HTTP ' + str(response.status_code))
            release = response.json()
        else:
            raise RuntimeError('GitHub release lookup HTTP ' + str(existing.status_code))
        asset_info = []
        existing_assets = {asset['name']: asset for asset in release.get('assets', [])}
        for path in args.asset:
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            if path.name in existing_assets:
                asset = existing_assets[path.name]
                if asset.get('digest') != 'sha256:' + sha:
                    raise RuntimeError('existing release asset differs; refusing overwrite: ' + path.name)
            else:
                uploaded = client.post(release['upload_url'].split('{')[0], params={'name': path.name},
                                       content=path.read_bytes(), headers={'Content-Type': 'application/octet-stream'})
                if uploaded.status_code != 201:
                    raise RuntimeError('GitHub asset upload HTTP ' + str(uploaded.status_code))
                asset = uploaded.json()
            asset_info.append({'name': path.name, 'url': asset['browser_download_url'], 'sha256': sha, 'bytes': path.stat().st_size})
        print(json.dumps({'release_url': release['html_url'], 'release_id': release['id'], 'tag': TAG,
                          'target_commit': commit, 'assets': asset_info}, indent=2))


if __name__ == '__main__':
    main()
