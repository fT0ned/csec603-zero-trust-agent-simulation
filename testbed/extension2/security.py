"""Study002 repairs and audit-only classification; imports immutable crypto primitives."""
import copy
import json
import math
import re

from testbed.common import canonical, validate_action
from testbed.extension.security import (Issuer, ProofVerifier, actor_path, proof, public_jwk,
    classify, response_for as paa_response, authority as old_authority)


def normalize(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError('nonfinite intent number')
        return int(value) if value.is_integer() else value
    if isinstance(value, dict):
        return {key:normalize(item) for key,item in value.items()}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def intent_key(call):
    return canonical(normalize(call))


def authority(action, params, delegation, counters):
    validate_action(action, params)
    grant=copy.deepcopy(delegation)
    grant['expected_calls']=normalize(grant['expected_calls'])
    used=copy.deepcopy(counters)
    used['intents']={}
    for key,count in counters['intents'].items():
        normalized=intent_key(json.loads(key))
        used['intents'][normalized]=used['intents'].get(normalized,0)+count
    return old_authority(action,normalize(params),grant,used)


def provenance_links(params, observed, intended):
    links=[]
    def strings(value):
        if isinstance(value,str):yield value
        elif isinstance(value,dict):
            for v in value.values():yield from strings(v)
        elif isinstance(value,list):
            for v in value:yield from strings(v)
    for parameter,value in params.items():
        for record in observed:
            texts=[record['text']]
            try:texts.extend(strings(json.loads(record['text'])))
            except (ValueError,TypeError):pass
            if isinstance(value,str) and len(value)>=4:
                matched=any(value in text for text in texts)
            elif type(value) in (int,float):
                # Typed JSON field in actual returned document/tool result.
                token=re.escape(str(normalize(value)))
                matched=any(re.search(r'"'+re.escape(parameter)+r'"\s*:\s*'+token+r'(?:\.0)?(?=[,}\s])',text) for text in texts)
            else:
                matched=False
            if matched:
                links.append({'parameter':parameter,'source_request_id':record['request_id'],'content_hash':record['content_hash'],
                    'already_in_principal_intent':any(c['params'].get(parameter)==value for c in intended)})
    return links


def response_for(signals,strategy='PAA'):
    if strategy=='PAA':
        return paa_response(signals)
    if strategy!='authority-only':
        raise ValueError('unknown study002 response policy')
    if not signals['possession_valid']:
        return 'refuse_request'
    if not signals['authority_valid']:
        return 'deny_keep_identity'
    return 'allow'
