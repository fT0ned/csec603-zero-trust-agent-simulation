"""C3 proof-of-possession: valid proof passes; missing/wrong-key/ath/replay/stale denied; other conditions unaffected."""
import time
from unittest.mock import patch
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
import jwt
from fastapi.testclient import TestClient
from testbed import binding, service
from testbed.common import digest

TOKEN = 'header.payload.signature'
HTU = 'http://gateway:8000/tool'

@pytest.fixture
def key(): return ec.generate_private_key(ec.SECP256R1())

def jkt(key): return binding.thumbprint(jwt.algorithms.ECAlgorithm.to_jwk(key.public_key(), as_dict=True))

def check(proof, key, seen=None, token=TOKEN, now=None):
    return binding.verify_proof(proof, token, jkt(key), 'POST', HTU, {} if seen is None else seen, now)

def test_thumbprint_is_canonical_sha256_of_required_members():
    import base64, hashlib
    jwk = {'kty': 'EC', 'crv': 'P-256', 'x': 'AAAA', 'y': 'BBBB', 'extra': 'ignored'}
    expected = base64.urlsafe_b64encode(hashlib.sha256(b'{"crv":"P-256","kty":"EC","x":"AAAA","y":"BBBB"}').digest()).rstrip(b'=').decode()
    assert binding.thumbprint(jwk) == expected

def test_valid_proof_passes(key): assert check(binding.make_proof(key, TOKEN, 'POST', HTU), key) == (True, 'valid')
def test_missing_proof(key): assert check('', key) == (False, 'binding_proof_missing')
def test_wrong_key(key):
    other = ec.generate_private_key(ec.SECP256R1())
    assert check(binding.make_proof(other, TOKEN, 'POST', HTU), key) == (False, 'binding_proof_invalid')
def test_ath_mismatch(key): assert check(binding.make_proof(key, 'other.token.value', 'POST', HTU), key) == (False, 'binding_proof_invalid')
def test_wrong_method_or_url(key):
    assert not check(binding.make_proof(key, TOKEN, 'GET', HTU), key)[0]
    assert not check(binding.make_proof(key, TOKEN, 'POST', 'http://evil/tool'), key)[0]
def test_replayed_jti(key):
    seen = {}; proof = binding.make_proof(key, TOKEN, 'POST', HTU)
    assert check(proof, key, seen)[0] and check(proof, key, seen) == (False, 'binding_proof_invalid')
def test_stale_and_future_iat(key):
    assert not check(binding.make_proof(key, TOKEN, 'POST', HTU, iat=int(time.time()) - 120), key)[0]
    assert not check(binding.make_proof(key, TOKEN, 'POST', HTU, iat=int(time.time()) + 120), key)[0]
    assert check(binding.make_proof(key, TOKEN, 'POST', HTU, iat=int(time.time()) - 30), key)[0]
def test_garbage_and_private_jwk_rejected(key):
    assert check('not.a.jwt', key) == (False, 'binding_proof_invalid')

def validate(condition, key, proof):
    state = {'condition': condition, 'credential_id': digest(TOKEN), 'spiffe_id': 's', 'revoked': False, 'binding_jkt': jkt(key), 'jwks': {'keys': [{'kid': 'k'}]}}
    fake = type('J', (), {'get_unverified_header': staticmethod(lambda t: {'alg': 'ES256', 'kid': 'k'}),
        'PyJWK': type('P', (), {'from_dict': staticmethod(lambda j: type('K', (), {'key': None})())}),
        'decode': staticmethod(lambda *a, **k: {'sub': 's'})})
    with patch.object(service, 'ADMIN', 'a'), patch.object(service, 'jwt', fake), patch.dict(service.RUNS, {'r': state}, clear=True), TestClient(service.app) as client:
        body = {'run_id': 'r', 'token': TOKEN, 'dpop': proof, 'htm': 'POST', 'htu': HTU}
        return client.post('/control/validate', headers={'x-admin-secret': 'a'}, json=body).json()

def test_c3_validate_requires_bound_proof(key):
    good = binding.make_proof(key, TOKEN, 'POST', HTU)
    assert validate('C3', key, good)['valid']
    assert validate('C3', key, '')['reason'] == 'binding_proof_missing'
    assert validate('C3', key, binding.make_proof(ec.generate_private_key(ec.SECP256R1()), TOKEN, 'POST', HTU))['reason'] == 'binding_proof_invalid'

def test_bearer_only_conditions_unaffected(key):
    for condition in ('C0', 'C1', 'C2', 'C2-noWF', 'C2-RS', 'C2-AS'):
        assert validate(condition, key, '') == {'valid': True, 'reason': 'valid', 'credential_id': digest(TOKEN)}
