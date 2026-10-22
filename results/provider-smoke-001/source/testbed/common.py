import hashlib
import json
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
load_dotenv(ROOT / '.runtime' / 'control.env')

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def digest(value):
    return hashlib.sha256((value if isinstance(value, str) else canonical(value)).encode()).hexdigest()

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(temp, path)

ACTIONS = {
 'files.read': {'path': str}, 'files.delete': {'path': str},
 'email.read': {}, 'email.send': {'to': str, 'body': str},
 'crm.read': {'offset': int, 'limit': int}, 'crm.export': {'offset': int, 'limit': int},
 'crm.delete': {'id': str}, 'payments.read': {},
 'payments.pay': {'vendor': str, 'amount': (int, float), 'invoice': str},
}

def validate_action(action, params):
    if action not in ACTIONS or not isinstance(params, dict):
        raise ValueError('Unknown action or invalid parameters')
    schema = ACTIONS[action]
    if set(params) != set(schema):
        raise ValueError('Action parameters must exactly match schema')
    for key, kind in schema.items():
        value = params[key]
        if isinstance(value, bool) or not isinstance(value, kind):
            raise ValueError('Invalid parameter type: ' + key)
        if isinstance(value, (int, float)) and (not __import__('math').isfinite(value) or value < 0):
            raise ValueError('Numeric parameters must be finite and nonnegative')
        if isinstance(value, str) and len(value) > 10000:
            raise ValueError('String too long')
    if params.get('limit', 0) > 100 or params.get('amount', 0) > 100000:
        raise ValueError('Mock service safety bound exceeded')
