from testbed.authorization_study import fixture
from testbed.common import canonical
from testbed.extension.security import authority as frozen_authority
from testbed.intent_normalization import hardened_authority, intent_key


def payment(amount):
    return {'action': 'payments.pay', 'params': {'vendor': 'vendor-1', 'amount': amount, 'invoice': 'invoice-approved'}}


def test_numeric_representation_cannot_spend_one_intent_twice():
    delegation = fixture('positive-payment')['delegation']
    first, second = payment(25), payment(25.0)
    counters = {'records': 0, 'payment': 25, 'intents': {canonical(first): 1}}
    assert frozen_authority(second['action'], second['params'], delegation, counters)[0]  # preserved v1 counterexample
    assert not hardened_authority(second['action'], second['params'], delegation, counters)[0]


def test_reverse_numeric_representation_and_first_float_authorization():
    delegation = fixture('positive-payment')['delegation']
    first, second = payment(25.0), payment(25)
    counters = {'records': 0, 'payment': 25, 'intents': {canonical(first): 1}}
    assert not hardened_authority(second['action'], second['params'], delegation, counters)[0]
    assert hardened_authority(first['action'], first['params'], delegation, {'records': 0, 'payment': 0, 'intents': {}})[0]
    assert intent_key(first) == intent_key(second)


def test_requested_multiplicity_is_preserved_and_third_use_refused():
    delegation = fixture('positive-payment')['delegation']
    delegation['expected_calls'] = [payment(25), payment(25)]
    call = payment(25.0)
    assert hardened_authority(call['action'], call['params'], delegation,
                              {'records': 0, 'payment': 25, 'intents': {canonical(payment(25)): 1}})[0]
    assert not hardened_authority(call['action'], call['params'], delegation,
                                  {'records': 0, 'payment': 50, 'intents': {canonical(payment(25)): 1, canonical(payment(25.0)): 1}})[0]


def test_representation_fix_does_not_authorize_unknown_invoice_or_bool_amount():
    delegation = fixture('positive-payment')['delegation']
    call = payment(25)
    call['params']['invoice'] = 'unrequested'
    assert not hardened_authority(call['action'], call['params'], delegation, {'records': 0, 'payment': 0, 'intents': {}})[0]
    call = payment(True)
    assert not hardened_authority(call['action'], call['params'], delegation, {'records': 0, 'payment': 0, 'intents': {}})[0]
