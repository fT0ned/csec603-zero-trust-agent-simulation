"""Real model choices after an audited forced-read prelude; no model fallback."""
import copy
import json
import os
import time

import httpx

from testbed.agent import Budget,ProviderFailure,provider_for,measured_cost
from testbed.common import canonical,validate_action
from testbed.fixtures import tools_schema
from .fixtures import MODELS


def application_view(value):
    result=value.get('result')
    if isinstance(result,dict) and 'result' in result:
        result=result['result']
    view={'outcome':value['outcome'],'result':result}
    if value['outcome']=='denied':view['reason']=value['audit']['authority_reason']
    return view


def exposed(messages,content):
    def leaves(value):
        if isinstance(value,str):yield value
        elif isinstance(value,dict):
            for v in value.values():yield from leaves(v)
        elif isinstance(value,list):
            for v in value:yield from leaves(v)
    return any(content in list(leaves(json.loads(m['content']))) for m in messages if m['role']=='tool')


def prelude(task,system_prompt,read_value):
    return [{'role':'system','content':system_prompt},{'role':'user','content':task},
            {'role':'assistant','content':'','tool_calls':[{'id':'required-document-read','type':'function',
                'function':{'name':'files_read','arguments':'{"path":"brief"}'}}]},
            {'role':'tool','tool_call_id':'required-document-read','name':'files_read','content':canonical(application_view(read_value))}]


def native_messages(messages):
    output=copy.deepcopy(messages)
    for m in output:
        for call in m.get('tool_calls',[]):
            args=call['function']['arguments']
            if isinstance(args,str):call['function']['arguments']=json.loads(args)
    return output


def loop(task,invoke,transcript,*,model,system_prompt,seed,read_value,content,max_steps=4,record_invalid=None):
    if model not in MODELS:raise ValueError('unregistered model')
    local=model not in MODELS[:2]
    spec={'input_miss_peak_per_million':0,'output_peak_per_million':0} if local else provider_for(model)
    messages=prelude(task,system_prompt,read_value)
    if not exposed(messages,content):raise RuntimeError('required payload absent from first tool history')
    key=None if local else os.getenv(spec['key_env'])
    if not local and not key:raise ProviderFailure('missing provider credential','provider_credentials_missing')
    budget=Budget(25);cost=0.;usage={'prompt_tokens':0,'completion_tokens':0};returned=[];errors=[];observed=False;contexts=[]
    result=lambda status:{'status':status,'cost_usd':cost,'usage':usage,'returned_models':returned,'model_errors':errors,
                          'exposure':True if observed else None,'local_context_observations':contexts,
                          'prelude_class':'harness-forced actual tool read; subsequent writes are model-generated'}
    with httpx.Client(timeout=180,trust_env=False) as client:
        for step in range(max_steps):
            if local:
                payload={'model':model,'messages':native_messages(messages),'tools':tools_schema(),'stream':False,
                         'options':{'temperature':0,'seed':seed,'num_ctx':4096,'num_predict':512},'keep_alive':'2m'}
                endpoint='http://127.0.0.1:11434/api/chat'
            else:
                payload={'model':model,'messages':copy.deepcopy(messages),'tools':tools_schema(),'temperature':0,'max_tokens':512}
                if spec['provider']=='deepseek':payload['thinking']={'type':'disabled'}
                else:payload.update(parallel_tool_calls=False,store=False)
                endpoint=spec['endpoint']
            for attempt in range(4):
                ceiling=((len(canonical(payload).encode())+10000)*spec['input_miss_peak_per_million']+512*spec['output_peak_per_million'])/1e6
                rid=budget.reserve(ceiling);start=time.time()
                try:
                    response=client.post(endpoint,json=payload,headers={'Authorization':'Bearer '+key} if key else {})
                except httpx.HTTPError as exc:
                    transcript.append({'request':payload,'reservation_id':rid,'reserved_usd':ceiling,'started_at':start,'error':type(exc).__name__})
                    raise ProviderFailure('provider transport failure; reservation retained','provider_transport_error',result('provider_failure')) from exc
                end=time.time()
                if response.status_code==429:
                    transcript.append({'request':payload,'reservation_id':rid,'reserved_usd':ceiling,'started_at':start,'finished_at':end,'http_status':429,'retry_attempt':attempt})
                    if attempt<3:time.sleep(2**attempt);continue
                if response.status_code!=200:
                    transcript.append({'request':payload,'reservation_id':rid,'reserved_usd':ceiling,'started_at':start,'finished_at':end,'http_status':response.status_code})
                    raise ProviderFailure('provider HTTP '+str(response.status_code),'provider_http_error',result('provider_failure'))
                try:
                    data=response.json();message=data['message'] if local else data['choices'][0]['message']
                    actual=data['model']
                    accepted=[model] if local else spec['accepted_response_models']
                    if actual not in accepted or message.get('role')!='assistant':raise ValueError('model/role mismatch')
                    current={'prompt_tokens':data['prompt_eval_count'],'completion_tokens':data['eval_count']} if local else data['usage']
                    charge={'cost_usd':0.,'pricing_note':'local inference; electricity unmeasured'} if local else measured_cost(current,spec,start,end)
                except (KeyError,TypeError,ValueError) as exc:
                    raise ProviderFailure('invalid provider response; reservation retained','provider_response_error',result('provider_failure')) from exc
                budget.settle(rid,charge['cost_usd']);cost+=charge['cost_usd']
                returned.append(actual)
                for field in usage:usage[field]+=current[field]
                transcript.append({'request':copy.deepcopy(payload),'response':data,'reservation_id':rid,'started_at':start,'finished_at':end,**charge})
                observed=True
                if local and not contexts:
                    try:
                        loaded=client.get('http://127.0.0.1:11434/api/ps').json()['models']
                        contexts.extend({k:item.get(k) for k in ('name','digest','context_length','size','size_vram')} for item in loaded if item['name']==model)
                    except (httpx.HTTPError,ValueError,KeyError):
                        contexts.append({'context_observation_error':True})
                break
            message={k:copy.deepcopy(v) for k,v in message.items() if k in ('role','content','tool_calls')}
            calls=message.get('tool_calls') or []
            for index,call in enumerate(calls):
                call.setdefault('id','model-'+str(step)+'-'+str(index));call.setdefault('type','function')
                if isinstance(call['function']['arguments'],dict):call['function']['arguments']=canonical(call['function']['arguments'])
            messages.append(message)
            if not calls:
                limited=(data.get('done_reason')=='length' if local else data['choices'][0].get('finish_reason')=='length')
                return result('model_step_limit' if limited else 'completed')
            for call in calls:
                action=None;params=None
                try:
                    action=call['function']['name'].replace('_','.',1)
                    params=json.loads(call['function']['arguments']);validate_action(action,params)
                except (ValueError,TypeError,KeyError) as exc:
                    value={'outcome':'model_error','error_type':type(exc).__name__};errors.append(value)
                    if record_invalid:
                        record_invalid(action,params,type(exc).__name__)
                else:value=application_view(invoke({'action':action,'params':params}))
                messages.append({'role':'tool','tool_call_id':call['id'],'name':call['function']['name'],'content':canonical(value)})
    return result('model_step_limit')
