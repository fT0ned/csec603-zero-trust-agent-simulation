"""Explicit laboratory capability, DPoP and PAA primitives. No harness truth input."""
from __future__ import annotations

import copy
import math
import posixpath
import re
import secrets
import time
import uuid
from urllib.parse import urlsplit, urlunsplit

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from testbed.binding import ath, thumbprint
from testbed.common import canonical, digest

ISSUER = 'https://extension-sts.csec603.test'
AUDIENCE = 'csec603-extension-tools'
UNRESERVED = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'


def normalize_htu(url):
    parts = urlsplit(url)
    if parts.scheme.lower() not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise ValueError('absolute HTTP URI without userinfo required')
    scheme = parts.scheme.lower()
    host = parts.hostname.lower()
    if ':' in host:
        host = '[' + host + ']'
    if parts.port and (scheme, parts.port) not in (('http', 80), ('https', 443)):
        host += ':' + str(parts.port)
    path = re.sub(r'%([0-9a-fA-F]{2})', lambda m: chr(int(m[1], 16)) if chr(int(m[1], 16)) in UNRESERVED else '%' + m[1].upper(), parts.path or '/')
    # RFC 3986 dot-segment removal; preserve empty path segments.
    output = []
    for part in path.split('/'):
        if part == '.':
            continue
        if part == '..':
            if output:
                output.pop()
        else:
            output.append(part)
    path = '/'.join(output)
    if parts.path.endswith(('/.', '/..')) and not path.endswith('/'):
        path += '/'
    return urlunsplit((scheme, host, path or '/', '', ''))


def public_jwk(key):
    return jwt.algorithms.ECAlgorithm.to_jwk(key.public_key(), as_dict=True)


def proof(key, method, url, *, token=None, nonce=None, now=None, jti=None):
    claims = {'jti': jti or uuid.uuid4().hex, 'htm': method, 'htu': normalize_htu(url),
              'iat': int(time.time() if now is None else now)}
    if token is not None:
        claims['ath'] = ath(token)
    if nonce is not None:
        claims['nonce'] = nonce
    return jwt.encode(claims, key, algorithm='ES256', headers={'typ': 'dpop+jwt', 'jwk': public_jwk(key)})


class ProofVerifier:
    """Nonce and replay state belongs to verifier, never to untrusted request data."""
    def __init__(self):
        self.seen = {}
        self.nonces = {}

    def nonce(self, context, now=None):
        value = secrets.token_urlsafe(24)
        self.nonces[context] = (value, (time.time() if now is None else now) + 120)
        return value

    def check(self, encoded, method, url, context, *, binding=None, token=None, now=None):
        now = time.time() if now is None else now
        try:
            header = jwt.get_unverified_header(encoded)
            jwk = header['jwk']
            if header.get('typ') != 'dpop+jwt' or header.get('alg') != 'ES256' or jwk.get('kty') != 'EC' or jwk.get('crv') != 'P-256' or 'd' in jwk:
                raise ValueError('proof header')
            jkt = thumbprint(jwk)
            if binding is not None and jkt != binding:
                raise ValueError('binding mismatch')
            claims = jwt.decode(encoded, jwt.PyJWK.from_dict(jwk).key, algorithms=['ES256'],
                                options={'verify_aud': False, 'verify_iat': False, 'require': ['jti', 'htm', 'htu', 'iat', 'nonce']})
            if type(claims['iat']) is not int or abs(now - claims['iat']) > 60:
                raise ValueError('proof age')
            if claims['htm'] != method or claims['htu'] != normalize_htu(url) or '?' in claims['htu'] or '#' in claims['htu']:
                raise ValueError('HTTP target')
            if not isinstance(claims['jti'], str) or not 1 <= len(claims['jti']) <= 200:
                raise ValueError('proof id')
            nonce, expiry = self.nonces.get(context, (None, 0))
            if not nonce or claims['nonce'] != nonce or expiry < now:
                return False, 'use_dpop_nonce', None
            if token is not None and claims.get('ath') != ath(token):
                raise ValueError('access token hash')
            self.seen = {k: expiry for k, expiry in self.seen.items() if expiry >= now}
            replay = (jkt, claims['jti'])
            if replay in self.seen:
                raise ValueError('proof replay')
            self.seen[replay] = now + 120
            return True, 'valid', jkt
        except (ValueError, TypeError, KeyError, jwt.PyJWTError):
            return False, 'invalid_dpop_proof', None


def decode_cap(token, key):
    return jwt.decode(token, key, algorithms=['ES256'], audience=AUDIENCE, issuer=ISSUER,
                      options={'require': ['iss', 'aud', 'sub', 'exp', 'iat', 'jti', 'task', 'scope', 'budget', 'act']})


def actor_path(claims):
    actors = []
    current = claims.get('act')
    while current:
        if not isinstance(current, dict) or not isinstance(current.get('sub'), str) or len(actors) > 8:
            raise ValueError('malformed actor chain')
        actors.append(current['sub'])
        current = current.get('act')
    return [claims['sub'], *reversed(actors)]


class Issuer:
    def __init__(self, key=None):
        self.key = key or ec.generate_private_key(ec.SECP256R1())
        self.ledger = {}
        self.revoked = set()

    def root(self, task, principal, scope, budget, next_actor, ttl=900):
        self._validate_budget(budget)
        now = int(time.time())
        claims = {'iss': ISSUER, 'aud': AUDIENCE, 'sub': principal, 'iat': now, 'exp': now + ttl,
                  'jti': uuid.uuid4().hex, 'task': task, 'scope': sorted(scope), 'budget': copy.deepcopy(budget),
                  'act': {}, 'next_actor': next_actor, 'parent': None}
        return self._sign(claims)

    def _sign(self, claims):
        token = jwt.encode(claims, self.key, algorithm='ES256', headers={'typ': 'at+jwt'})
        self.ledger[digest(token)] = copy.deepcopy(claims)
        return token

    @staticmethod
    def _validate_budget(budget):
        if not isinstance(budget, dict) or not budget or any(not isinstance(k, str) or isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for k, v in budget.items()):
            raise ValueError('finite nonnegative capability budgets required')

    def verify(self, token, *, enforce_chain=True, require_live=True):
        claims = decode_cap(token, self.key.public_key())
        visited = set()
        current_token, current = token, claims
        while True:
            token_id = digest(current_token) if current_token is not None else parent_id
            if token_id in visited or len(visited) > 8:
                raise ValueError('chain cycle/depth')
            visited.add(token_id)
            if self.ledger.get(token_id) != current:
                raise ValueError('unregistered or truncated capability')
            if require_live and (token_id in self.revoked or current['act'].get('sub') in self.revoked):
                raise ValueError('revoked capability/ancestor')
            parent_id = current.get('parent')
            if parent_id is None:
                if current['act']:
                    raise ValueError('missing root')
                break
            parent = self.ledger.get(parent_id)
            if parent is None:
                raise ValueError('missing parent')
            if current['sub'] != parent['sub'] or current['task'] != parent['task'] or current['exp'] > parent['exp']:
                raise ValueError('parent context mismatch')
            if current['act'] != {'sub': parent['next_actor'], **({'act': parent['act']} if parent['act'] else {})}:
                raise ValueError('actor-chain mismatch')
            if enforce_chain:
                if not set(current['scope']) <= set(parent['scope']):
                    raise ValueError('scope widening')
                if set(current['budget']) != set(parent['budget']) or any(current['budget'][k] > parent['budget'][k] for k in parent['budget']):
                    raise ValueError('budget widening')
            current_token, current = None, parent
        return claims

    def exchange(self, parent_token, actor, scope, budget, next_actor, *, jkt=None, enforce=True, actor_svid_digest=None):
        self._validate_budget(budget)
        parent = self.verify(parent_token, enforce_chain=enforce)
        if actor != parent['next_actor']:
            raise ValueError('exchange actor not authorized')
        if enforce and (not set(scope) <= set(parent['scope']) or set(budget) != set(parent['budget']) or any(budget[k] > parent['budget'][k] for k in budget)):
            raise ValueError('exchange widens authority')
        claims = {**copy.deepcopy(parent), 'jti': uuid.uuid4().hex, 'iat': int(time.time()), 'scope': sorted(scope), 'budget': copy.deepcopy(budget),
                  'parent': digest(parent_token), 'next_actor': next_actor,
                  'act': {'sub': actor, **({'act': parent['act']} if parent['act'] else {})}}
        if actor_svid_digest is not None:
            claims['actor_svid_digest'] = actor_svid_digest
        if jkt:
            claims['cnf'] = {'jkt': jkt}
        else:
            claims.pop('cnf', None)
        return self._sign(claims)


def authority(action, params, delegation, counters):
    """PDP authority evaluation. Approval uses an explicit one-use intended-call set."""
    if action not in delegation['actions']:
        return False, 'scope_denied'
    if action == 'crm.export' and (params['limit'] > delegation['max_per_records'] or counters['records'] + params['limit'] > delegation['max_records']):
        return False, 'workflow_limit'
    if action == 'payments.pay' and (params['vendor'] not in delegation['vendors'] or params['amount'] > delegation['max_per_payment'] or counters['payment'] + params['amount'] > delegation['max_payment']):
        return False, 'payment_authority'
    if action == 'email.send' and params['to'] not in delegation['recipients']:
        return False, 'recipient_authority'
    if action in ('email.send', 'payments.pay', 'crm.delete', 'files.delete'):
        call = {'action': action, 'params': params}
        if delegation['expected_calls'].count(call) <= counters['intents'].get(canonical(call), 0):
            return False, 'intent_denied'
    return True, 'allowed'


def classify(audit):
    """Audit-only: exposure/benign copied parameters alone never imply coercion."""
    if audit.get('origin') and audit.get('expected_origin') and audit['origin'] != audit['expected_origin']:
        return 'impersonation'
    introduced = [link for link in audit.get('parameter_provenance', []) if not link.get('already_in_principal_intent', False)]
    if audit.get('identity_valid') and not audit.get('authority_valid', True) and introduced:
        return 'coercion'
    return 'none'


def response_for(signals, strategy='PAA'):
    if strategy not in ('PAA', 'suspend-all'):
        raise ValueError('unknown response strategy')
    anomaly = (not signals['possession_valid'] or signals['classification'] != 'none' or not signals['authority_valid'] or signals.get('accountability') != 'complete')
    if strategy == 'suspend-all' and anomaly:
        return 'suspend_identity'
    if signals['classification'] == 'impersonation' and signals['possession_valid']:
        return 'revoke_credential'
    if not signals['possession_valid']:
        return 'refuse_request'
    if signals.get('accountability') == 'tamper':
        return 'contain_identity'
    if signals.get('accountability') == 'gap':
        return 'escalate'
    if not signals['authority_valid']:
        return 'deny_keep_identity_flag_input' if signals['classification'] == 'coercion' else 'deny_keep_identity'
    return 'allow'
