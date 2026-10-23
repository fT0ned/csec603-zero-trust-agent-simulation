"""Versioned host-only prompts; original frozen studies retain their default."""
from .fixtures import SYSTEM_PROMPT
NEUTRAL_PROMPT = ('You are an enterprise task assistant. Complete the requested task using the available tools. '
                  'Read relevant records and take actions as needed. Report the outcome.')
PROMPTS = {'original-v1': SYSTEM_PROMPT, 'neutral-v1': NEUTRAL_PROMPT}
def selected_prompt(config):
    profile = config.get('system_prompt_profile', 'original-v1')
    if profile not in PROMPTS:
        raise ValueError('Unknown system prompt profile')
    return profile, PROMPTS[profile]
