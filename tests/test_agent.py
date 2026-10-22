"""Mock-transport verification; these are software tests, not study results."""
import concurrent.futures
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import httpx
from testbed import agent

HTTPClient=httpx.Client

class FakeBudget:
    def __init__(self):self.reservations=[];self.settlements=[]
    def reserve(self,amount):self.reservations.append(amount);return len(self.reservations)
    def settle(self,reservation,actual):self.settlements.append((reservation,actual))

def response(message=None,model='deepseek-flash',**extra):
    return {'model':model,'system_fingerprint':'mock-fingerprint',
            'choices':[{'message':message or {'role':'assistant','content':'Done'},'finish_reason':'stop'}],
            'usage':{'prompt_tokens':100,'completion_tokens':20,'prompt_cache_hit_tokens':40,'prompt_cache_miss_tokens':60},**extra}

class ProviderTests(unittest.TestCase):
    def setUp(self):agent._CATALOGUE.clear()
    def execute(self,replies,invoke=lambda call:{'outcome':'executed'},model='deepseek-flash'):
        requests=[];budget=FakeBudget();transcript=[]
        def handler(request):
            if request.method=='GET':
                return httpx.Response(200,json={'data':[{'id':'deepseek-flash'},{'id':'gpt-4.1-mini-2025-04-14'}]})
            requests.append(json.loads(request.content))
            reply=replies[len(requests)-1]
            if isinstance(reply,int):return httpx.Response(reply,json={'error':'mock provider failure'})
            return httpx.Response(200,json=reply)
        transport=httpx.MockTransport(handler)
        factory=lambda **kwargs:HTTPClient(transport=transport,**kwargs)
        with patch.dict(os.environ,{'DEEPSEEK_API_KEY':'mock-key-not-a-credential','OPENAI_API_KEY':'mock-openai-not-a-credential'}),patch.object(agent.httpx,'Client',factory):
            result=agent.llm_loop('Mock task',invoke,transcript,budget,model=model)
        return result,requests,budget,transcript

    def test_deepseek_explicit_settings_usage_and_metadata(self):
        result,requests,budget,transcript=self.execute([response()])
        payload=requests[0]
        self.assertEqual(payload['thinking'],{'type':'disabled'})
        self.assertEqual(payload['temperature'],0)
        self.assertEqual(payload['max_tokens'],1024)
        self.assertNotIn('store',payload)
        self.assertEqual(result['model_snapshots'],['deepseek-flash'])
        self.assertEqual(result['system_fingerprints'],['mock-fingerprint'])
        self.assertFalse(result['model_metadata']['immutable_snapshot'])
        self.assertIn('response',result['provider_catalogue'])
        self.assertEqual(result['usage']['prompt_tokens'],100)
        self.assertGreater(budget.reservations[0],budget.settlements[0][1])
        self.assertNotIn('mock-key-not-a-credential',json.dumps(transcript))

    def test_openai_is_explicit_not_fallback(self):
        result,requests,_,_=self.execute([response(model='gpt-4.1-mini-2025-04-14')],model='gpt-4.1-mini-2025-04-14')
        self.assertEqual(result['provider'],'openai')
        self.assertNotIn('thinking',requests[0])
        self.assertFalse(requests[0]['store'])
        with self.assertRaises(ValueError):agent.provider_for('unreviewed-model')

    def test_calls_are_real_invoke_and_transcript_requests_do_not_mutate(self):
        called=[]
        tool={'role':'assistant','content':None,'tool_calls':[{'id':'tool1','type':'function','function':{'name':'files_read','arguments':'{"path":"brief"}'}}]}
        result,requests,_,transcript=self.execute([response(tool),response()],lambda call:called.append(call) or {'outcome':'executed','result':'Mock data'})
        self.assertEqual(called,[{'action':'files.read','params':{'path':'brief'}}])
        self.assertEqual(len(transcript[0]['request']['messages']),2)
        self.assertEqual(len(requests[1]['messages']),4)
        self.assertEqual(len(result['cost_records']),2)

    def test_model_invalid_arguments_remain_a_model_error(self):
        called=[]
        tool={'role':'assistant','content':None,'tool_calls':[{'id':'tool1','type':'function','function':{'name':'crm_export','arguments':'{"offset":-1,"limit":5}'}}]}
        result,_,_,_=self.execute([response(tool),response()],lambda call:called.append(call))
        self.assertFalse(called)
        self.assertEqual(len(result['model_errors']),1)

    def test_provider_error_retains_reservation_and_partial_evidence(self):
        with self.assertRaises(agent.ProviderFailure) as caught:self.execute([500])
        error=caught.exception
        self.assertEqual(error.category,'provider_error')
        self.assertGreater(error.partial_result['uncertain_reservations_usd'],0)
        self.assertEqual(error.partial_result['cost_kind'],'price_ceiling_with_uncertain_request')

    def test_model_drift_fails_without_fallback_after_accounting(self):
        with self.assertRaises(agent.ProviderFailure) as caught:self.execute([response(model='unexpected-backend')])
        self.assertEqual(caught.exception.category,'provider_model_drift')
        self.assertGreater(caught.exception.partial_result['cost_usd'],0)

    def test_cache_and_offpeak_charge_is_precise_only_when_supported(self):
        epoch=lambda hour:datetime(2026,10,22,hour,tzinfo=timezone.utc).timestamp()
        usage={'prompt_tokens':100,'completion_tokens':20,'prompt_cache_hit_tokens':40,'prompt_cache_miss_tokens':60}
        spec=agent.provider_for('deepseek-flash')
        cost=agent.measured_cost(usage,spec,epoch(11),epoch(11)+2)
        self.assertAlmostEqual(cost['cost_usd'],(40*.003+60*.15+20*.6)/1e6)
        self.assertEqual(cost['cost_kind'],'usage_times_verified_rates')
        peak=agent.measured_cost(usage,spec,epoch(7),epoch(7)+2)
        self.assertEqual(peak['cost_kind'],'price_ceiling')
        self.assertEqual(peak['cost_usd'],2*cost['cost_usd'])
        unknown=agent.measured_cost({'prompt_tokens':100,'completion_tokens':20},spec,epoch(11),epoch(11)+2)
        self.assertEqual(unknown['cost_kind'],'price_ceiling')

    def test_budget_is_atomic_shared_and_uncertain_reservations_stay_spent(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'STUDY_BUDGET_USD':'1'}):
            budget=agent.Budget(5,path=Path(directory)/'spend.sqlite')
            def reserve(_):
                try:return budget.reserve(.2)
                except agent.ProviderFailure:return None
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                ids=[x for x in pool.map(reserve,range(12)) if x is not None]
            self.assertEqual(len(ids),5)
            other=agent.Budget(1,path=budget.path)
            with self.assertRaises(agent.ProviderFailure):other.reserve(.01)
            budget.settle(ids[0],.05)
            self.assertIsInstance(other.reserve(.1),int)
            with self.assertRaises(ValueError):budget.settle(ids[0],0)

if __name__=='__main__':unittest.main()
