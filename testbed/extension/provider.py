"""Extension-only explicit providers and 429 retries using the original shared Budget."""
from __future__ import annotations

import copy
import os
import time

import httpx

from testbed.agent import Budget, ProviderFailure, provider_for, measured_cost
from testbed.common import canonical, validate_action
from testbed.fixtures import tools_schema

MODELS = ('deepseek-flash', 'gpt-4.1-mini-2025-04-14', 'qwen2.5:7b-instruct', 'qwen2.5:3b-instruct')


def spec_for(model):
    if model in MODELS[:2]:
        return provider_for(model)
    if model in MODELS[2:]:
        return {'provider': 'ollama', 'endpoint': 'http://127.0.0.1:11434/v1/chat/completions',
                'accepted_response_models': [model], 'input_miss_peak_per_million': 0,
                'input_hit_peak_per_million': 0, 'output_peak_per_million': 0,
                'pricing_source': 'local inference; electricity not measured'}
    raise ValueError('unreviewed model')


def loop(task, invoke, transcript, *, model, system_prompt, seed, budget=None, max_steps=6):
    spec = spec_for(model)
    local = spec['provider'] == 'ollama'
    key = None if local else os.getenv(spec['key_env'])
    if not local and not key:
        raise ProviderFailure('provider credentials missing', 'provider_credentials_missing')
    budget = budget or Budget(25)
    messages = [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': task}]
    cost = 0.0
    returned = []
    errors = []
    usage_sum = {'prompt_tokens': 0, 'completion_tokens': 0}
    result = lambda status: {'status': status, 'cost_usd': cost, 'returned_models': returned,
                             'usage': usage_sum, 'model_errors': errors, 'model': model}
    with httpx.Client(timeout=180, trust_env=False) as client:
        for step in range(max_steps):
            payload = {'model': model, 'messages': messages, 'tools': tools_schema(), 'temperature': 0, 'max_tokens': 768}
            if local:
                payload['seed'] = seed
            elif spec['provider'] == 'deepseek':
                payload['thinking'] = {'type': 'disabled'}
            else:
                payload.update(parallel_tool_calls=False, store=False)
            for attempt in range(4):
                upper = ((len(canonical(payload).encode()) + 10000) * spec['input_miss_peak_per_million'] + 768 * spec['output_peak_per_million']) / 1e6
                rid = budget.reserve(upper)
                started = time.time()
                try:
                    response = client.post(spec['endpoint'], json=payload, headers={'Authorization': 'Bearer ' + key} if key else {})
                except httpx.HTTPError as exc:
                    transcript.append({'request': copy.deepcopy(payload), 'reservation_id': rid, 'reserved_usd': upper,
                                       'error': type(exc).__name__, 'started_at': started})
                    failure = ProviderFailure('provider transport failure; reservation retained', 'provider_transport_error', result('provider_failure'))
                    raise failure from exc
                finished = time.time()
                if response.status_code == 429:
                    transcript.append({'request': copy.deepcopy(payload), 'reservation_id': rid, 'reserved_usd': upper,
                                       'http_status': 429, 'retry_attempt': attempt, 'started_at': started, 'finished_at': finished})
                    if attempt < 3:
                        time.sleep(2 ** attempt)
                        continue
                if response.status_code != 200:
                    transcript.append({'request': copy.deepcopy(payload), 'reservation_id': rid, 'reserved_usd': upper,
                                       'http_status': response.status_code, 'started_at': started, 'finished_at': finished})
                    raise ProviderFailure('provider HTTP ' + str(response.status_code) + '; reservation retained', 'provider_http_error', result('provider_failure'))
                try:
                    data = response.json()
                    charge = measured_cost(data['usage'], spec, started, finished)
                    actual_model = data['model']
                    message = data['choices'][0]['message']
                    if actual_model not in spec['accepted_response_models'] or message.get('role') != 'assistant':
                        raise ValueError('model/role drift')
                except (ValueError, KeyError, IndexError, TypeError) as exc:
                    raise ProviderFailure('provider response validation failed; reservation retained', 'provider_response_error', result('provider_failure')) from exc
                budget.settle(rid, charge['cost_usd'])
                cost += charge['cost_usd']
                returned.append(actual_model)
                for field in usage_sum:
                    usage_sum[field] += data['usage'][field]
                transcript.append({'request': copy.deepcopy(payload), 'response': data, 'reservation_id': rid,
                                   'started_at': started, 'finished_at': finished, **charge})
                break
            message = {k: v for k, v in message.items() if k in ('role', 'content', 'tool_calls')}
            messages.append(message)
            calls = message.get('tool_calls') or []
            if not calls:
                return result('model_step_limit' if data['choices'][0].get('finish_reason') == 'length' else 'completed')
            for call in calls:
                try:
                    import json
                    action = call['function']['name'].replace('_', '.', 1)
                    params = json.loads(call['function']['arguments'])
                    validate_action(action, params)
                except (ValueError, KeyError, TypeError) as exc:
                    value = {'outcome': 'model_error', 'error_type': type(exc).__name__}
                    errors.append(value)
                else:
                    value = invoke({'action': action, 'params': params})
                messages.append({'role': 'tool', 'tool_call_id': call.get('id', 'missing'), 'content': canonical(value)})
    return result('model_step_limit')
