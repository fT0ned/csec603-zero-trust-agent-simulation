"""DPoP-style proof of possession (RFC 9449 spirit; RFC 7638 thumbprints). Used only by C3/C3-AS.

The agent-client container holds an EC P-256 private key; the harness registers its JWK thumbprint
as the credential binding. Each request carries a JWS over htm/htu/iat/jti/ath signed by that key.
"""
import base64
import hashlib
import json
import os
import time
import uuid
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

SKEW = 60

def _b64(data): return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

def thumbprint(jwk):
    """RFC 7638 SHA-256 thumbprint of an EC public JWK."""
    return _b64(hashlib.sha256(json.dumps({k: jwk[k] for k in ('crv', 'kty', 'x', 'y')}, sort_keys=True, separators=(',', ':')).encode()).digest())

def ath(token): return _b64(hashlib.sha256(token.encode()).digest())

def generate_key(path):
    """Create a P-256 key readable only by the calling UID; return its public JWK."""
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream: stream.write(pem)
    return jwt.algorithms.ECAlgorithm.to_jwk(key.public_key(), as_dict=True)

def load_key(path):
    with open(path, 'rb') as stream: return serialization.load_pem_private_key(stream.read(), None)

def make_proof(key, token, htm, htu, iat=None, jti=None):
    jwk = jwt.algorithms.ECAlgorithm.to_jwk(key.public_key(), as_dict=True)
    claims = {'htm': htm, 'htu': htu, 'iat': int(time.time()) if iat is None else iat, 'jti': jti or uuid.uuid4().hex, 'ath': ath(token)}
    return jwt.encode(claims, key, algorithm='ES256', headers={'typ': 'dpop+jwt', 'jwk': jwk})

def verify_proof(proof, token, binding_jkt, htm, htu, seen, now=None):
    """Return (ok, reason). ``seen`` is the per-run jti replay cache (mutated on success)."""
    if not proof: return False, 'binding_proof_missing'
    now = time.time() if now is None else now
    try:
        header = jwt.get_unverified_header(proof)
        jwk = header.get('jwk')
        if header.get('typ') != 'dpop+jwt' or header.get('alg') != 'ES256' or not isinstance(jwk, dict) or jwk.get('kty') != 'EC' or 'd' in jwk: raise ValueError('header')
        if thumbprint(jwk) != binding_jkt: raise ValueError('key not bound to credential')
        claims = jwt.decode(proof, jwt.PyJWK.from_dict(jwk).key, algorithms=['ES256'],
                            options={'verify_exp': False, 'verify_aud': False, 'verify_iat': False, 'require': ['htm', 'htu', 'iat', 'jti', 'ath']})
        if claims['htm'] != htm or claims['htu'] != htu or claims['ath'] != ath(token): raise ValueError('claim mismatch')
        if not isinstance(claims['iat'], int) or abs(now - claims['iat']) > SKEW: raise ValueError('stale iat')
        if not isinstance(claims['jti'], str) or claims['jti'] in seen: raise ValueError('replayed jti')
    except Exception:
        return False, 'binding_proof_invalid'
    seen[claims['jti']] = claims['iat']
    for old in [j for j, t in seen.items() if now - t > 2 * SKEW]: seen.pop(old)
    return True, 'valid'
