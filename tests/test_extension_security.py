import copy
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from testbed.binding import thumbprint
from testbed.extension.security import Issuer, ProofVerifier, actor_path, authority, classify, normalize_htu, proof, public_jwk, response_for
from testbed.extension.fixtures import fixture, FAMILIES, WORKLOADS


def test_normalization_and_target_integrity():
    assert normalize_htu('HTTPS://EXAMPLE.test:443/a/%7euser/../b?x=1#f') == 'https://example.test/a/b'
    assert normalize_htu('http://example.test:80') == 'http://example.test/'
    assert normalize_htu('https://example.test/a//b') == 'https://example.test/a//b'
    assert normalize_htu('https://example.test:8443/a/%2f') == 'https://example.test:8443/a/%2F'
    with pytest.raises(ValueError):
        normalize_htu('https://user:password@example.test/a')


def test_nonce_binding_hash_age_signature_replay():
    verifier = ProofVerifier()
    key, wrong = ec.generate_private_key(ec.SECP256R1()), ec.generate_private_key(ec.SECP256R1())
    now = time.time()
    nonce = verifier.nonce('task', now)
    jkt = thumbprint(public_jwk(key))
    good = proof(key, 'POST', 'https://example.test/a?ignored=1', token='access', nonce=nonce, now=now)
    assert verifier.check(good, 'POST', 'https://example.test/a?different=2', 'task', binding=jkt, token='access', now=now)[0]
    assert not verifier.check(good, 'POST', 'https://example.test/a', 'task', binding=jkt, token='access', now=now)[0]
    for args in [dict(token='other', nonce=nonce), dict(token='access', nonce='wrong'), dict(token='access', nonce=nonce, now=now-100)]:
        p = proof(key, 'POST', 'https://example.test/a', **args)
        assert not verifier.check(p, 'POST', 'https://example.test/a', 'task', binding=jkt, token='access', now=now)[0]
    p = proof(wrong, 'POST', 'https://example.test/a', token='access', nonce=nonce)
    assert not verifier.check(p, 'POST', 'https://example.test/a', 'task', binding=jkt, token='access')[0]
    p = proof(key, 'GET', 'https://example.test/a', token='access', nonce=nonce)
    assert not verifier.check(p, 'POST', 'https://example.test/a', 'task', binding=jkt, token='access')[0]
    p = proof(key, 'POST', 'https://example.test/b', token='access', nonce=nonce)
    assert not verifier.check(p, 'POST', 'https://example.test/a', 'task', binding=jkt, token='access')[0]


def test_signed_attenuation_chain_forgery_truncation_cascade():
    issuer = Issuer()
    root = issuer.root('task', 'human', ['read', 'write'], {'records': 10}, 'A')
    a = issuer.exchange(root, 'A', ['read'], {'records': 5}, 'B')
    b = issuer.exchange(a, 'B', ['read'], {'records': 2}, '')
    assert actor_path(issuer.verify(b)) == ['human', 'A', 'B']
    for parent, actor in [(root, 'A'), (a, 'B')]:
        with pytest.raises(ValueError):
            issuer.exchange(parent, actor, ['delete'], {'records': 20}, '')
    with pytest.raises(ValueError):
        issuer.exchange(root, 'B', ['read'], {'records': 1}, '')
    claims = issuer.verify(b)
    claims['act'] = {'sub': 'B'}
    truncated = jwt.encode(claims, issuer.key, algorithm='ES256')
    with pytest.raises(ValueError):
        issuer.verify(truncated)
    forged = jwt.encode(claims, ec.generate_private_key(ec.SECP256R1()), algorithm='ES256')
    with pytest.raises(jwt.PyJWTError):
        issuer.verify(forged)
    issuer.revoked.add('A')
    with pytest.raises(ValueError):
        issuer.verify(b)


def test_baseline_does_not_disable_cryptographic_integrity():
    issuer = Issuer()
    root = issuer.root('task', 'human', ['read'], {'records': 1}, 'A')
    wider = issuer.exchange(root, 'A', ['read', 'delete'], {'records': 10}, 'B', enforce=False)
    assert issuer.verify(wider, enforce_chain=False)['scope'] == ['delete', 'read']
    with pytest.raises(ValueError):
        issuer.verify(wider)
    with pytest.raises(jwt.PyJWTError):
        issuer.verify(wider[:-8] + 'AAAAAAAA', enforce_chain=False)


def test_audit_classifier_has_no_truth_input_and_avoids_benign_provenance():
    base = {'origin': 'A', 'expected_origin': 'A', 'identity_valid': True, 'authority_valid': True,
            'parameter_provenance': [{'parameter': 'path'}]}
    assert classify(base) == 'none'
    assert classify({**base, 'authority_valid': False}) == 'coercion'
    assert classify({**base, 'authority_valid': False, 'parameter_provenance': []}) == 'none'
    assert classify({**base, 'origin': 'thief'}) == 'impersonation'
    assert classify({'ground_truth': 'coercion', 'scenario': 'coercion'}) == 'none'


@pytest.mark.parametrize('signals,expected', [
    ({'possession_valid': False, 'authority_valid': True, 'classification': 'impersonation', 'accountability': 'complete'}, 'refuse_request'),
    ({'possession_valid': True, 'authority_valid': True, 'classification': 'impersonation', 'accountability': 'complete'}, 'revoke_credential'),
    ({'possession_valid': True, 'authority_valid': False, 'classification': 'coercion', 'accountability': 'complete'}, 'deny_keep_identity_flag_input'),
    ({'possession_valid': True, 'authority_valid': False, 'classification': 'none', 'accountability': 'complete'}, 'deny_keep_identity'),
    ({'possession_valid': True, 'authority_valid': True, 'classification': 'none', 'accountability': 'gap'}, 'escalate'),
    ({'possession_valid': True, 'authority_valid': True, 'classification': 'none', 'accountability': 'tamper'}, 'contain_identity')])
def test_paa_invariants_and_uniform_comparator(signals, expected):
    assert response_for(signals) == expected
    assert response_for(signals, 'suspend-all') == 'suspend_identity'


def test_all_workload_positive_and_negative_controls():
    for family in FAMILIES:
        for workload in WORKLOADS:
            fixed = fixture(family, 181000, workload)
            counters = {'records': 0, 'payment': 0, 'intents': {}}
            assert authority(fixed['good']['action'], fixed['good']['params'], fixed['delegation'], counters)[0]
            assert not authority(fixed['bad']['action'], fixed['bad']['params'], fixed['delegation'], counters)[0]
            assert all(str(v) in fixed['content'] for v in fixed['bad']['params'].values())
