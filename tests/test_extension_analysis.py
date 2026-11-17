from testbed.extension.analyse import holm, rate, summary_group


def test_holm_family_keeps_missing_comparisons_conservative():
    tests = [{'p_value': .02}, {'p_value': None}, {'p_value': .04}]
    holm(tests)
    assert tests[0]['p_holm'] == .06
    assert tests[1]['p_holm'] == 1
    assert tests[2]['p_holm'] == .08


def test_missing_is_never_counted_as_a_negative_outcome():
    value = rate([True, False, None])
    assert value['n'] == 2 and value['successes'] == 1 and value['missing'] == 1
