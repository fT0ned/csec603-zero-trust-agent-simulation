"""Verify public release assets against local bytes and immutable tag targets."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import httpx
from testbed.common import ROOT,write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--asset',type=Path,action='append',required=True)
    args=parser.parse_args();api='https://api.github.com/repos/fT0ned/csec603-zero-trust-agent-simulation'
    tag='extension-study-002'
    commit=subprocess.check_output(['git','rev-list','-n','1',tag],cwd=ROOT,text=True).strip()
    tag_object=subprocess.check_output(['git','rev-parse',tag],cwd=ROOT,text=True).strip()
    with httpx.Client(timeout=120,trust_env=False,follow_redirects=True,headers={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2026-03-10'}) as client:
        release=client.get(api+'/releases/tags/'+tag);release.raise_for_status();release=release.json()
        if release['tag_name']!=tag or release['draft']:raise ValueError('Unexpected release state')
        ref=client.get(api+'/git/ref/tags/'+tag);ref.raise_for_status();ref=ref.json()
        if ref['object']['sha']!=tag_object:raise ValueError('Public archive tag differs')
        if ref['object']['type']=='tag':
            target=client.get(api+'/git/tags/'+tag_object);target.raise_for_status();target=target.json()['object']['sha']
        else:target=ref['object']['sha']
        if target!=commit:raise ValueError('Archive commit mismatch')
        by={a['name']:a for a in release['assets']};checked=[]
        for path in args.asset:
            local=hashlib.sha256(path.read_bytes()).hexdigest();asset=by[path.name]
            if asset.get('digest')!='sha256:'+local:raise ValueError('GitHub asset digest mismatch')
            sha=hashlib.sha256();size=0
            with client.stream('GET',asset['browser_download_url']) as downloaded:
                downloaded.raise_for_status()
                for block in downloaded.iter_bytes():sha.update(block);size+=len(block)
            if sha.hexdigest()!=local or size!=path.stat().st_size:raise ValueError('Public downloaded bytes differ')
            checked.append({'name':path.name,'sha256':local,'bytes':size,'public_url':asset['browser_download_url'],'download_verified':True})
    result={'checked_at':time.time(),'passed':True,'tag':tag,'tag_object':tag_object,'target_commit':commit,
            'release_url':release['html_url'],'assets':checked}
    write_json(ROOT/'docs/extension-study-002-release-verification.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
