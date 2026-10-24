"""Hash-chain validation with independent count/hash checkpoint."""
import json
from pathlib import Path
from .common import digest

def verify(records, checkpoint):
    previous = '0' * 64
    count = 0
    try:
        for number, record in enumerate(records, 1):
            count = number
            row = dict(record)
            claimed = row.pop('hash', None)
            if row.get('previous_hash') != previous or row.get('sequence') != number or digest(row) != claimed:
                return {'valid': False, 'reason': 'chain mismatch', 'record': number, 'count': count}
            previous = claimed
    except (OSError,ValueError,TypeError) as error:
        return {'valid': False, 'reason': 'unreadable audit: '+type(error).__name__, 'count': count}
    valid = checkpoint.get('count') == count and checkpoint.get('hash') == previous
    return {'valid': valid, 'reason': 'verified' if valid else 'checkpoint mismatch', 'count': count}

def iter_audit_files(paths):
    """Read raw JSONL chunks in the supplied order, retaining one record only."""
    for path in paths:
        with Path(path).open(encoding='utf-8') as stream:
            for line in stream:
                yield json.loads(line)

def tamper_files(paths, checkpoint):
    """Test five fixed alterations of raw JSONL chunks with constant memory.

    Each case opens a fresh reader. Chunk order is supplied by the caller (base
    first, then numbered rotations); paths are never lexicographically sorted.
    Original files and the independent checkpoint remain unchanged.
    """
    paths = tuple(paths)
    count = checkpoint.get('count', 0)
    if not isinstance(count,int) or count < 0:
        raise ValueError('Checkpoint count must be a nonnegative integer')
    if count == 0:
        return {}
    def altered():
        for index, record in enumerate(iter_audit_files(paths)):
            if index == 0:
                record = dict(record)
                record['result'] = 'tamper-test:'+str(record.get('result'))
            yield record
    def deleted(target):
        for index, record in enumerate(iter_audit_files(paths)):
            if index != target:
                yield record
    def reordered():
        stream = iter_audit_files(paths)
        sentinel = object()
        first = next(stream,sentinel)
        second = next(stream,sentinel)
        if second is not sentinel:
            yield second
        if first is not sentinel:
            yield first
        yield from stream
    cases = {'alter':altered(), 'delete_middle':deleted(count//2),
             'delete_tail':deleted(count-1), 'delete_all':iter(())}
    if count > 1:
        cases['reorder'] = reordered()
    return {name:verify(rows,checkpoint) for name,rows in cases.items()}

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
    coercion = False
    for row in records:
        if row.get('origin') and row.get('expected_origin') and row['origin'] != row['expected_origin']:
            return 'impersonation'
        # Exact parameter provenance from observed tool content; harmless exposure alone is insufficient.
        if row.get('parameter_provenance'):
            coercion = True
    return 'coercion' if coercion else 'none'
