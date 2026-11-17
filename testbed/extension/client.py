"""Container-side requests. Keys stay in the actor container; credentials only on stdin."""
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

from testbed.binding import generate_key, load_key
from testbed.extension.security import proof


def post(url, body, headers=None):
    request = urllib.request.Request(url, json.dumps(body).encode('utf-8'), {'Content-Type': 'application/json', **(headers or {})})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            value, status = json.load(response), response.status
    except urllib.error.HTTPError as error:
        value, status = json.loads(error.read()), error.code
    return {'status': status, 'data': value, 'latency_ms': (time.perf_counter() - started) * 1000}


def main(data):
    run_id = data['run_id']
    if not run_id.replace('-', '').replace('_', '').isalnum():
        raise ValueError('unsafe key id')
    base = Path('/tmp/extension-keys')
    base.mkdir(mode=0o700, exist_ok=True)
    key_id = data.get('key_id') or run_id
    if not key_id.replace('-', '').replace('_', '').isalnum():
        raise ValueError('unsafe key id')
    path = base / (key_id + '.pem')
    mode = data['mode']
    if mode == 'keygen':
        return {'status': 200, 'data': {'jwk': generate_key(str(path))}}
    if mode == 'cleanup':
        path.unlink(missing_ok=True)
        return {'status': 200, 'data': {}}
    url = 'http://extension-pep:8000/' + ('exchange' if mode == 'exchange' else 'tool')
    headers = {}
    sign_ms = 0.0
    if mode == 'tool':
        headers['Authorization'] = ('DPoP ' if data.get('bound') else 'Bearer ') + data['token']
    if data.get('sign'):
        context = ('exchange:' if mode == 'exchange' else 'resource:') + run_id
        nonce = post('http://extension-pep:8000/nonce', {'context': context})['data']['nonce']
        started = time.perf_counter()
        headers['DPoP'] = proof(load_key(path), 'POST', url, token=data.get('token') if mode == 'tool' else None, nonce=nonce)
        sign_ms = (time.perf_counter() - started) * 1000
    value = post(url, data['body'], headers)
    value['sign_ms'] = sign_ms
    return value


if __name__ == '__main__':
    print(json.dumps(main(json.load(sys.stdin))))
