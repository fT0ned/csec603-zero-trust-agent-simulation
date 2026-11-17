"""Correct tool/system visibility for mandatory-tool-read continuations.

New local profile names, identical base weights, no generation calls. Preserve
stock tags and the entire original pilot. Full held-out matrix is unchanged.
"""
import hashlib
import json
import re
from pathlib import Path

import httpx

from testbed.common import ROOT,write_json

PROFILES={
    'llama3.2:3b-instruct-q4_K_M':'study002-llama3b-tools:v1',
    'mistral:7b-instruct':'study002-mistral7b-tools:v1'}


def corrected_template(model,template):
    if model.startswith('llama3.2'):
        old='{{- if and $.Tools $last }}'
        if template.count(old)!=1:raise ValueError('unexpected stock Llama template')
        return template.replace(old,'{{- if $.Tools }}')
    if model.startswith('mistral'):
        tools='{{- if and (eq (len (slice $.Messages $index)) 1) $.Tools }}'
        system='{{ if and $.System (eq (len (slice $.Messages $index)) 1) }}'
        if template.count(tools)!=1 or template.count(system)!=1:raise ValueError('unexpected stock Mistral template')
        return template.replace(tools,'{{- if $.Tools }}').replace(system,'{{ if $.System }}')
    raise ValueError('unregistered template repair')


def main():
    config_path=ROOT/'configs/extension-study-002.json'
    config=json.loads(config_path.read_text(encoding='utf-8'))
    record={}
    with httpx.Client(trust_env=False,timeout=180) as client:
        for base,profile in PROFILES.items():
            show=client.post('http://127.0.0.1:11434/api/show',json={'model':base});show.raise_for_status();stock=show.json()
            recipe={'model':profile,'from':base,'template':corrected_template(base,stock['template']),'stream':False}
            created=client.post('http://127.0.0.1:11434/api/create',json=recipe);created.raise_for_status()
            shown=client.post('http://127.0.0.1:11434/api/show',json={'model':profile});shown.raise_for_status();fixed=shown.json()
            stock_weights=re.search(r'^FROM (.+)$',stock['modelfile'],re.M).group(1)
            profile_weights=re.search(r'^FROM (.+)$',fixed['modelfile'],re.M).group(1)
            comparable=lambda details:{k:details.get(k) for k in ('format','family','families','parameter_size','quantization_level')}
            if fixed['model_info']!=stock['model_info'] or comparable(fixed['details'])!=comparable(stock['details']) or stock_weights!=profile_weights:
                raise ValueError('template profile changed weight/model metadata')
            tags={m['name']:m for m in client.get('http://127.0.0.1:11434/api/tags').json()['models']}
            if tags[base]['digest']!=config['local_model_digests'][base]:raise ValueError('base manifest changed')
            record[base]={'base_manifest_digest':tags[base]['digest'],'profile':profile,'profile_manifest_digest':tags[profile]['digest'],
                 'stock_template':stock['template'],'corrected_template':fixed['template'],'recipe':recipe,
                 'same_weight_metadata':True,'weight_blob':stock_weights,'stock_details':stock['details'],'profile_details':fixed['details'],
                 'generation_calls':0,'template_sha256':hashlib.sha256(fixed['template'].encode()).hexdigest()}
            expected=config.get('profile_model_digests',{}).get(profile)
            if expected and expected!=tags[profile]['digest']:raise ValueError('profile differs from pinned recipe')
    target=ROOT/'docs/extension-study-002-runtime-profiles.json'
    if target.exists() and json.loads(target.read_text(encoding='utf-8'))!=record:
        raise ValueError('existing profile specification differs')
    if not target.exists():write_json(target,record)
    print(json.dumps({base:{k:r[k] for k in ('profile','profile_manifest_digest','generation_calls')} for base,r in record.items()}))


if __name__=='__main__':main()
