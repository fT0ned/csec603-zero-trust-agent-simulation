"""Post-freeze engineering repair for semantic one-use intent accounting.

This helper is NOT installed in extension-study-freeze-v1 or used by its collected
conditions. It preserves that evidence while supplying a tested fix for future
integration. Numerically equal integral JSON representations share one intent.
"""
from __future__ import annotations

import copy
import json
import math

from testbed.common import canonical, validate_action
from testbed.extension.security import authority as frozen_authority


def normalize_numbers(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError('nonfinite intent number')
        return int(value) if value.is_integer() else value
    if isinstance(value, dict):
        return {k: normalize_numbers(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_numbers(v) for v in value]
    return value


def intent_key(call):
    return canonical(normalize_numbers(call))


def semantic_used_count(call, intents):
    target = intent_key(call)
    total = 0
    for key, count in intents.items():
        if type(count) is not int or count < 0:
            raise ValueError('invalid intent usage count')
        if intent_key(json.loads(key)) == target:
            total += count
    return total


def hardened_authority(action, params, delegation, counters):
    try:
        validate_action(action, params)
        call = {'action': action, 'params': params}
        corrected = copy.deepcopy(counters)
        corrected['intents'][canonical(call)] = semantic_used_count(call, counters['intents'])
    except (ValueError, TypeError, KeyError):
        return False, 'invalid_schema_or_intent_counter'
    return frozen_authority(action, params, delegation, corrected)
