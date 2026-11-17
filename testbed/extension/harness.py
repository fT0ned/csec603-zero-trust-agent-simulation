"""Trusted orchestrator helpers. Token bytes remain in memory and stdin pipes only."""
from __future__ import annotations

import base64
import json
import os
import subprocess
import time
import uuid

import httpx
import jwt

from scripts.spire import _server, _walk, _json_documents, compose, delete_registration, issue, AGENT_SOCKET, DOMAIN, NODE
from testbed.common import ROOT, canonical

ACTOR_SERVICES = {'A': 'agent-client', 'B': 'extension-agent-b'}


def container(service, data):
    process = subprocess.run(['docker', 'compose', 'exec', '-T', service, 'python', '-m', 'testbed.extension.client'],
                             input=canonical(data), text=True, encoding='utf-8', capture_output=True, cwd=ROOT, timeout=65)
    if process.returncode:
        # Do not interpolate raw subprocess stderr into evidence: validation errors
        # may otherwise accidentally retain credential-bearing request details.
        raise RuntimeError('extension client subprocess failed')
    value = json.loads(process.stdout)
    if value['status'] != 200 and not (value['status'] == 401 and value.get('data', {}).get('outcome') == 'denied'):
        raise RuntimeError('extension client HTTP ' + str(value['status']))
    return value


def admin(path, data=None, *, get=False):
    with httpx.Client(timeout=45, trust_env=False) as client:
        function = client.get if get else client.post
        response = function('http://127.0.0.1:8769' + path,
                            **({} if get else {'json': data or {}}), headers={'x-admin-secret': os.environ.get('ADMIN_SECRET', '')})
        response.raise_for_status()
        return response.json()


def origin(service):
    program = "import json,urllib.request;print(urllib.request.urlopen('http://extension-pep:8000/whoami').read().decode())"
    return json.loads(compose('exec', '-T', service, 'python', '-c', program))['origin']


def fetch_identity(spiffe_id, service):
    output = compose('exec', '-T', service, '/opt/spire/bin/spire-agent', 'api', 'fetch', 'jwt', '-socketPath', AGENT_SOCKET,
                     '-audience', 'csec603-gateway', '-spiffeID', spiffe_id, '-output', 'json')
    nodes = list(_walk(_json_documents(output)))
    token = next(n['svid'] for n in nodes if isinstance(n, dict) and isinstance(n.get('svid'), str))
    encoded = next(n['bundles'].get('spiffe://' + DOMAIN, n['bundles'].get(DOMAIN)) for n in nodes if isinstance(n, dict) and isinstance(n.get('bundles'), dict))
    try:
        jwks = json.loads(base64.b64decode(encoded))
    except (ValueError, json.JSONDecodeError):
        jwks = json.loads(encoded)
    return {'token': token, 'jwks': jwks, 'claims': jwt.decode(token, options={'verify_signature': False})}


class Actors:
    """Fresh workload registrations per process, refreshed before token expiry."""
    def __init__(self):
        self.identities = {}
        self.entries = []
        self.issuance_ms = []

    def __enter__(self):
        for actor, service in ACTOR_SERVICES.items():
            started = time.perf_counter()
            name = 'extension-' + actor + '-' + uuid.uuid4().hex
            if actor == 'A':
                identity = issue(name, 3600)
            else:
                spiffe_id = 'spiffe://' + DOMAIN + '/agent/' + name
                registered = _server('entry', 'create', '-parentID', NODE, '-spiffeID', spiffe_id,
                                     '-selector', 'unix:uid:10003', '-jwtSVIDTTL', '3600', '-output', 'json')
                entry_id = next(n['id'] for n in _walk(_json_documents(registered)) if isinstance(n, dict) and isinstance(n.get('id'), str))
                self.entries.append(entry_id)
                for attempt in range(30):
                    try:
                        identity = {**fetch_identity(spiffe_id, service), 'entry_id': entry_id, 'spiffe_id': spiffe_id}
                        break
                    except (RuntimeError, ValueError, StopIteration):
                        if attempt == 29:
                            raise
                        time.sleep(1)
            if identity['entry_id'] not in self.entries:
                self.entries.append(identity['entry_id'])
            identity['origin'] = origin(service)
            self.identities[actor] = identity
            self.issuance_ms.append({'actor': actor, 'ms': (time.perf_counter() - started) * 1000})
        return self

    def refresh(self, actor, force=False):
        identity = self.identities[actor]
        if force or identity['claims']['exp'] - time.time() < 300:
            started = time.perf_counter()
            identity.update(fetch_identity(identity['spiffe_id'], ACTOR_SERVICES[actor]))
            return (time.perf_counter() - started) * 1000
        return 0.0

    def public(self):
        return {a: {'spiffe_id': i['spiffe_id'], 'origin': i['origin']} for a, i in self.identities.items()}

    def __exit__(self, *args):
        for entry in self.entries:
            delete_registration(entry)


class Session:
    def __init__(self, actors, fixed, condition, strategy='PAA'):
        self.actors, self.fixed, self.condition = actors, fixed, condition
        self.run_id = 'ext-' + uuid.uuid4().hex
        self.bound = condition == 'C3-9449-E'
        self.tokens = {}
        self.claims = {}
        self.exchanges = []
        self.actions = []
        self.key_ids = {}
        self.generated_keys = []
        for actor in actors.identities:
            actors.refresh(actor)
        self.start = admin('/admin/start', {'run_id': self.run_id, 'condition': condition, 'strategy': strategy,
                                          'delegation': fixed['delegation'], 'content': fixed['content'],
                                          'actors': actors.public(), 'svid_jwks': actors.identities['A']['jwks']})
        self.root = self.start['root_token']
        self.budget = {'records': fixed['delegation']['max_records'], 'payment': fixed['delegation']['max_payment']}
        self.scope = fixed['delegation']['actions']

    def keygen(self, actor, recovery=False):
        key_id = self.run_id + ('-recovery' if recovery else '')
        self.key_ids[actor] = key_id
        container(ACTOR_SERVICES[actor], {'mode': 'keygen', 'run_id': key_id})
        self.generated_keys.append((actor, key_id))

    def exchange(self, actor='A', parent=None, scope=None, budget=None, next_actor=None):
        if self.bound and actor not in self.key_ids:
            self.keygen(actor)
        identity = self.actors.identities[actor]
        body = {'run_id': self.run_id, 'actor_token': identity['token'], 'subject_token': parent or self.root,
                'scope': self.scope if scope is None else scope, 'budget': self.budget if budget is None else budget,
                'next_actor': self.actors.identities['B']['spiffe_id'] if next_actor is None else next_actor}
        value = container(ACTOR_SERVICES[actor], {'mode': 'exchange', 'run_id': self.run_id, 'key_id': self.key_ids.get(actor),
                                                 'body': body, 'sign': self.bound})['data']
        self.exchanges.append({k: v for k, v in value.items() if k != 'access_token'})
        if value['ok']:
            self.tokens[actor], self.claims[actor] = value['access_token'], value['claims']
        return value

    def invoke(self, call, *, actor='A', thief=False, token=None):
        body = {'run_id': self.run_id, 'request_id': uuid.uuid4().hex, **call}
        selected = token if token is not None else self.start['static_token'] if self.condition == 'C0-E' else self.tokens[actor]
        value = container('attacker' if thief else ACTOR_SERVICES[actor],
                          {'mode': 'tool', 'run_id': self.run_id, 'key_id': self.key_ids.get(actor), 'body': body,
                           'token': selected, 'bound': self.bound, 'sign': self.bound and not thief})
        self.actions.append({'request': body, 'actor': actor, 'thief': thief, **value})
        return value['data']

    def evidence(self):
        return admin('/admin/evidence/' + self.run_id, get=True)

    def close(self):
        for actor, key_id in self.generated_keys:
            container(ACTOR_SERVICES[actor], {'mode': 'cleanup', 'run_id': key_id})
        admin('/admin/retire', {'run_id': self.run_id})
