"""Shared, conservative credential-validity endpoint classification.

Tool execution failures and policy denials are not credential-expiry events.
This module changes measurement only; it grants no authority or retry behavior.
"""
VALID = 'valid'
CREDENTIAL_DENIED = 'credential_denied'
CREDENTIAL_DENIAL_REASONS = frozenset({'revoked', 'invalid or expired JWT-SVID'})


class ProbeMeasurementError(RuntimeError):
    def __init__(self, category, status, payload):
        data = payload if isinstance(payload, dict) else {}
        self.details = {'category': category, 'http_status': status,
                        'outcome': data.get('outcome'), 'reason': data.get('reason')}
        super().__init__('Credential probe measurement failed: ' + category)


def classify_probe(status, payload):
    """Return valid/credential_denied or fail measurement; never infer expiry.

    The existing validator combines invalid and expired JWTs in one reason, so
    its endpoint establishes observed credential rejection, not exact expiry.
    """
    if status != 200:
        raise ProbeMeasurementError('transport_failure', status, payload)
    if not isinstance(payload, dict):
        raise ProbeMeasurementError('invalid_probe_response', status, payload)
    outcome, allowed, reason = payload.get('outcome'), payload.get('allowed'), payload.get('reason')
    if outcome == 'executed' and allowed is True and reason not in CREDENTIAL_DENIAL_REASONS:
        return VALID
    if outcome == 'denied' and allowed is False and reason in CREDENTIAL_DENIAL_REASONS:
        return CREDENTIAL_DENIED
    category = {'tool_error': 'tool_failure', 'infrastructure_error': 'infrastructure_failure',
                'denied': 'policy_failure'}.get(outcome, 'invalid_probe_response')
    raise ProbeMeasurementError(category, status, payload)
