import json
import pytest
from testbed.common import ROOT
from scripts.prepare_extension2_profiles import corrected_template


@pytest.mark.parametrize('model',['llama3.2:3b-instruct-q4_K_M','mistral:7b-instruct'])
def test_profile_fix_is_only_visibility_predicates_and_preserves_weight_identity(model):
    profiles=json.loads((ROOT/'docs/extension-study-002-runtime-profiles.json').read_text(encoding='utf-8'))
    p=profiles[model]
    assert corrected_template(model,p['stock_template'])==p['corrected_template']
    assert p['same_weight_metadata'] and p['generation_calls']==0
    assert 'sha256-' in p['weight_blob']
    assert 'if $.Tools' in p['corrected_template']
    assert 'if and $.Tools $last' not in p['corrected_template']
    if model.startswith('mistral'):
        assert 'if $.System' in p['corrected_template']
        assert 'if and $.System (eq' not in p['corrected_template']
