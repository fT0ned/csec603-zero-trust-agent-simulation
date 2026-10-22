"""Hash-chain validation with independent count/hash checkpoint."""
import json
from .common import digest

def verify(records, checkpoint):
    previous = '0' * 64
    for number, record in enumerate(records, 1):
        row = dict(record)
        claimed = row.pop('hash', None)
        if row.get('previous_hash') != previous or row.get('sequence') != number or digest(row) != claimed:
            return {'valid': False, 'reason': 'chain mismatch', 'record': number}
        previous = claimed
    valid = checkpoint.get('count') == len(records) and checkpoint.get('hash') == previous
    return {'valid': valid, 'reason': 'verified' if valid else 'checkpoint mismatch', 'count': len(records)}

def tamper_suite(records, checkpoint):
    import copy
    cases = {}
    if records:
        altered = copy.deepcopy(records); altered[0]['result'] = 'tampered'; cases['alter'] = altered
        cases['delete_middle'] = records[:len(records)//2] + records[len(records)//2+1:]
        cases['delete_tail'] = records[:-1]
        cases['delete_all'] = []
        if len(records) > 1:
            cases['reorder'] = [records[1], records[0], *records[2:]]
    return {name: verify(rows, checkpoint) for name, rows in cases.items()}

def attribution(records):
    # This function has no ground-truth input and consumes only condition-visible fields.
    for row in records:
        if row.get('origin') and row.get('expected_origin') and row['origin'] != row['expected_origin']:
            return 'impersonation'
    for row in records:
        # Exact parameter provenance from observed tool content; harmless exposure alone is insufficient.
        if row.get('parameter_provenance'):
            return 'coercion'
    return 'none'
