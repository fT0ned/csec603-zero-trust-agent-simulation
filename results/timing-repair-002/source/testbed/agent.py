"""Explicit providers, preserved evidence, and fail-closed spending reservations.

DeepSeek pricing/API fields verified on 2026-10-22 from official documentation.
There is no provider/model fallback. Alias metadata is not an immutable snapshot.
"""
from __future__ import annotations
import copy
from contextlib import closing
from datetime import datetime,timezone
import json
import math
import os
from pathlib import Path
import sqlite3
import threading
import time
import httpx
from .common import ROOT,canonical,validate_action
from .fixtures import SYSTEM_PROMPT,tools_schema

MODEL='deepseek-flash'
PROVIDERS={
 'deepseek-flash':{
  'provider':'deepseek','key_env':'DEEPSEEK_API_KEY','endpoint':'https://api.deepseek.com/chat/completions',
  'models_endpoint':'https://api.deepseek.com/models','documented_version':'DeepSeek-V4.1-Flash-1017',
  'immutable_snapshot':False,'accepted_response_models':['deepseek-flash','DeepSeek-V4.1-Flash-1017'],
  'input_miss_peak_per_million':.30,'input_hit_peak_per_million':.006,'output_peak_per_million':1.20,
  'pricing_source':'https://api-docs.deepseek.com/quick_start/pricing/',
  'api_source':'https://api-docs.deepseek.com/api/create-chat-completion/','verified_on':'2026-10-22'},
 'gpt-4.1-mini-2025-04-14':{
  'provider':'openai','key_env':'OPENAI_API_KEY','endpoint':'https://api.openai.com/v1/chat/completions',
  'models_endpoint':'https://api.openai.com/v1/models/gpt-4.1-mini-2025-04-14',
  'documented_version':'gpt-4.1-mini-2025-04-14','immutable_snapshot':True,
  'accepted_response_models':['gpt-4.1-mini-2025-04-14'],
  'input_miss_peak_per_million':.40,'input_hit_peak_per_million':.40,'output_peak_per_million':1.60,
  'pricing_source':'https://platform.openai.com/docs/pricing',
  'cost_note':'Existing reviewed miss-token ceiling; cached-token discounts are not credited.'},
}
INPUT_RATE=PROVIDERS[MODEL]['input_miss_peak_per_million']/1_000_000
OUTPUT_RATE=PROVIDERS[MODEL]['output_peak_per_million']/1_000_000
_CATALOGUE={}
_CATALOGUE_LOCK=threading.Lock()

class ProviderFailure(RuntimeError):
    """Retain this experimental unit; do not infrastructure-rerun it."""
    def __init__(self,message,category='provider_error',partial_result=None):
        super().__init__(message);self.category=category;self.partial_result=partial_result or {}

def provider_for(model):
    if model not in PROVIDERS:raise ValueError('Unreviewed model/provider; select an explicitly supported model')
    return copy.deepcopy(PROVIDERS[model])

class Budget:
    def __init__(self,requested,path=None):
        established=float(os.getenv('STUDY_BUDGET_USD','0'))
        if not math.isfinite(established) or not math.isfinite(float(requested)) or established<=0 or requested<=0:
            raise ValueError('Set an established positive STUDY_BUDGET_USD and batch budget')
        self.limit=min(established,float(requested));self.path=Path(path) if path else ROOT/'.runtime'/'spend.sqlite'
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS spend (id INTEGER PRIMARY KEY, reserved REAL, actual REAL, state TEXT)')
    def reserve(self,amount):
        if not math.isfinite(amount) or amount<0:raise ValueError('Invalid reservation amount')
        with closing(sqlite3.connect(self.path,timeout=30)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            used=db.execute('SELECT coalesce(sum(coalesce(actual,reserved)),0) FROM spend').fetchone()[0]
            if used+amount>self.limit:raise ProviderFailure('Spending limit exhausted; uncertain reservations retained','budget_exhausted')
            return db.execute('INSERT INTO spend(reserved,state) VALUES (?,?)',(amount,'reserved')).lastrowid
    def settle(self,reservation,actual):
        if not math.isfinite(actual) or actual<0:raise ValueError('Invalid settlement amount')
        with closing(sqlite3.connect(self.path,timeout=30)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT reserved,state FROM spend WHERE id=?',(reservation,)).fetchone()
            if row is None or row[1]!='reserved':raise ValueError('Unknown or previously settled reservation')
            db.execute('UPDATE spend SET actual=?,state=? WHERE id=?',(actual,'settled',reservation))
        if actual>row[0]+1e-12:raise ProviderFailure('Cost exceeded reservation; actual recorded; stop collection','budget_bound_exceeded')

def certainly_off_peak(started,finished):
    """Known off-peak intervals avoid guessing Chinese public holidays."""
    if finished<started or finished-started>300:return False
    for epoch in [started,finished]+list(range(int(started),int(finished)+1,60)):
        utc=datetime.fromtimestamp(epoch,timezone.utc)
        if utc.weekday()<5 and (1<=utc.hour<4 or 6<=utc.hour<10):return False
    return True

def measured_cost(usage,spec,started,finished):
    for field in ('prompt_tokens','completion_tokens'):
        if not isinstance(usage.get(field),int) or isinstance(usage[field],bool) or usage[field]<0:
            raise ValueError('Missing or invalid provider token usage')
    prompt,completion=usage['prompt_tokens'],usage['completion_tokens']
    hit=usage.get('prompt_cache_hit_tokens',usage.get('prompt_tokens_details',{}).get('cached_tokens'))
    miss=usage.get('prompt_cache_miss_tokens')
    if hit is not None and miss is None:miss=prompt-hit
    breakdown=(isinstance(hit,int) and isinstance(miss,int) and not isinstance(hit,bool)
               and not isinstance(miss,bool) and hit>=0 and miss>=0 and hit+miss==prompt)
    off_peak=spec['provider']=='deepseek' and certainly_off_peak(started,finished)
    multiplier=.5 if off_peak else 1.
    if not breakdown:hit,miss=0,prompt
    cost=(miss*spec['input_miss_peak_per_million']+hit*spec['input_hit_peak_per_million']
          +completion*spec['output_peak_per_million'])*multiplier/1_000_000
    return {'cost_usd':cost,'cost_kind':'usage_times_verified_rates' if spec['provider']=='deepseek' and off_peak and breakdown else 'price_ceiling',
            'off_peak_certified':off_peak,'cache_breakdown_complete':breakdown,
            'prompt_cache_hit_tokens':hit if breakdown else None,'prompt_cache_miss_tokens':miss if breakdown else None,
            'pricing_source':spec['pricing_source'],
            'note':'Computed token charge; account-balance reconciliation is separate. Peak/holiday ambiguity or missing cache details uses a ceiling.'}

def _catalogue(client,spec,key):
    name=spec['provider']
    with _CATALOGUE_LOCK:
        if name not in _CATALOGUE:
            try:
                response=client.get(spec['models_endpoint'],headers={'Authorization':'Bearer '+key})
                if response.status_code!=200:raise ValueError('Catalogue HTTP error')
                data=response.json()
                advertised=[x.get('id') for x in data.get('data',[])] if 'data' in data else [data.get('id')]
            except Exception as error:
                raise ProviderFailure('Provider model catalogue unavailable: '+type(error).__name__,'provider_metadata_error') from error
            if not any(x in advertised for x in spec['accepted_response_models']):
                raise ProviderFailure('Configured model absent from catalogue','provider_metadata_error')
            _CATALOGUE[name]={'fetched_at':time.time(),'endpoint':spec['models_endpoint'],'response':data}
        return copy.deepcopy(_CATALOGUE[name])

def llm_loop(task,invoke,transcript,budget,model=MODEL,max_steps=12):
    spec=provider_for(model);key=os.getenv(spec['key_env'])
    if not key:raise ProviderFailure(spec['key_env']+' is missing','provider_credentials_missing')
    messages=[{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':task}]
    total_cost=0.;uncertain=0.;usage_total={'prompt_tokens':0,'completion_tokens':0}
    snapshots=[];fingerprints=[];cost_records=[];model_errors=[];catalogue=None
    def partial(exhausted=False):
        return {'cost_usd':total_cost,'cost_kind':'price_ceiling_with_uncertain_request' if uncertain else
                'usage_times_verified_rates' if cost_records and all(x['cost_kind']=='usage_times_verified_rates' for x in cost_records) else 'price_ceiling',
                'uncertain_reservations_usd':uncertain,'usage':dict(usage_total),'model_snapshots':list(snapshots),
                'system_fingerprints':list(fingerprints),'cost_records':list(cost_records),'provider':spec['provider'],
                'model_metadata':{k:v for k,v in spec.items() if k!='key_env'},'provider_catalogue':catalogue,
                'model_errors':list(model_errors),'exhausted':exhausted}
    def fail(message,category='provider_error'):raise ProviderFailure(message,category,partial())
    tools=tools_schema()
    with httpx.Client(timeout=90,trust_env=False) as client:
        try:catalogue=_catalogue(client,spec,key)
        except ProviderFailure as error:error.partial_result=partial();raise
        for step in range(max_steps):
            payload={'model':model,'messages':messages,'tools':tools,'temperature':0,'max_tokens':1024}
            if spec['provider']=='deepseek':payload['thinking']={'type':'disabled'}
            else:payload.update(parallel_tool_calls=False,store=False)
            input_bound=len(canonical(payload).encode('utf-8'))+10000
            upper=(input_bound*spec['input_miss_peak_per_million']+1024*spec['output_peak_per_million'])/1_000_000
            try:reservation=budget.reserve(upper)
            except ProviderFailure as error:error.partial_result=partial();raise
            started=time.time();request_copy=copy.deepcopy(payload);data=None
            try:response=client.post(spec['endpoint'],json=payload,headers={'Authorization':'Bearer '+key})
            except httpx.HTTPError as error:
                uncertain+=upper
                transcript.append({'provider':spec['provider'],'request':request_copy,'error':type(error).__name__,
                                   'time':started,'reservation_id':reservation,'reserved_usd':upper})
                fail('Provider transport failure; reservation retained','provider_transport_error')
            finished=time.time()
            if response.status_code!=200:
                uncertain+=upper
                try:error_response=json.loads(json.dumps(response.json()).replace(key,'[REDACTED_PROVIDER_KEY]'))
                except ValueError:error_response={'body':response.text.replace(key,'[REDACTED_PROVIDER_KEY]')}
                transcript.append({'provider':spec['provider'],'request':request_copy,'status':response.status_code,
                                   'error':'Provider request failed','time':started,'finished_at':finished,
                                   'response':error_response,'reservation_id':reservation,'reserved_usd':upper})
                fail('Provider HTTP '+str(response.status_code)+'; reservation retained')
            try:data=response.json();usage=data['usage'];charge=measured_cost(usage,spec,started,finished)
            except (ValueError,KeyError,TypeError,AttributeError):
                uncertain+=upper
                transcript.append({'provider':spec['provider'],'request':request_copy,'error':'Invalid provider response/usage',
                                   'response':data,'time':started,'reservation_id':reservation,'reserved_usd':upper})
                fail('Provider response lacks valid usage; reservation retained','provider_response_error')
            cost=charge['cost_usd'];total_cost+=cost
            cost_records.append(dict(charge,reservation_id=reservation,started_at=started,finished_at=finished))
            for k in usage_total:usage_total[k]+=usage[k]
            actual_model=data.get('model');snapshots.append(actual_model);fingerprints.append(data.get('system_fingerprint'))
            transcript.append({'provider':spec['provider'],'request':request_copy,'response':data,'time':started,
                               'finished_at':finished,'reservation_id':reservation,'reserved_usd':upper,**charge})
            try:budget.settle(reservation,cost)
            except ProviderFailure as error:error.partial_result=partial();raise
            if actual_model not in spec['accepted_response_models']:
                fail('Returned model differs from reviewed provider/model','provider_model_drift')
            try:
                choice=data['choices'][0];message=choice['message']
                if message.get('role')!='assistant':raise ValueError('Unexpected response role')
                message={k:v for k,v in message.items() if k in ('role','content','tool_calls')}
                messages.append(message);calls=message.get('tool_calls') or []
            except (ValueError,KeyError,IndexError,TypeError,AttributeError):
                fail('Provider response lacks valid assistant choice','provider_response_error')
            finish_reason=choice.get('finish_reason')
            if not calls:
                if finish_reason in ('content_filter','insufficient_system_resource','aborted'):
                    fail('Provider terminated completion: '+finish_reason,'provider_completion_error')
                return partial(exhausted=finish_reason=='length')
            for call in calls:
                try:
                    action=call['function']['name'].replace('_','.',1);params=json.loads(call['function']['arguments'])
                    validate_action(action,params);result=invoke({'action':action,'params':params})
                except (ValueError,KeyError,TypeError) as error:
                    result={'outcome':'model_error','error':type(error).__name__+': '+str(error)}
                    model_errors.append({'step':step,'tool_call_id':call.get('id'),'result':result})
                messages.append({'role':'tool','tool_call_id':call.get('id','missing-id'),'content':canonical(result)})
    return partial(exhausted=True)
