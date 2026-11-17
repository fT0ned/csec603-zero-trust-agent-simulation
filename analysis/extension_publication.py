"""Post-freeze presentation layer. Reads sealed analyzer outputs; adds no samples/tests."""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from analysis.statistics import describe, wilson
from testbed.common import ROOT, write_json
from testbed.extension.analyse import ci_text, continuous_text, latex_table, rate, table


def save(out, name, headers, rows):
    (out / (name + '.md')).write_text(table(headers, rows), encoding='utf-8')
    (out / (name + '.tex')).write_text(latex_table(headers, rows), encoding='utf-8')


def memory_bytes(text):
    match = re.match(r'([0-9.]+)\s*([KMGT]?i?B)', text)
    if not match:
        return None
    value, unit = float(match[1]), match[2]
    powers = {'B': 1, 'kB': 1000, 'KB': 1000, 'MB': 1e6, 'GB': 1e9, 'KiB': 1024, 'MiB': 1024**2, 'GiB': 1024**3, 'TiB': 1024**4}
    return value * powers[unit]


def publish(root):
    root = Path(root)
    report = json.loads((root / 'analysis/report.json').read_text(encoding='utf-8'))
    rows = json.loads((root / 'analysis/primary-rows.json').read_text(encoding='utf-8'))
    out = root / 'publication'
    out.mkdir(exist_ok=True)
    selected = lambda **fields: [r for r in rows if all(r.get(k) == v for k, v in fields.items())]
    table_rows = []
    for c in ('C0-E', 'C2-E', 'C3-9449-E'):
        group = selected(experiment='E1-scripted', condition=c)
        table_rows.append([c, len(group), ci_text(rate([r.get('injection_followed') for r in group])),
                           ci_text(rate([r.get('unauthorized_outcome') for r in group])),
                           ci_text(rate([r.get('legitimate_available') for r in group]))])
    save(out, 'coerced-agent-controls', ['Condition', 'Scripted n', 'Payload attempt, Wilson 95%', 'Unauthorized write effect, Wilson 95%', 'Authorized action after, Wilson 95%'], table_rows)
    table_rows = []
    for case in ('positive', 'widen-A', 'widen-B', 'forged', 'truncated', 'stolen-B', 'revoke-A'):
        groups = [selected(experiment='E2', case=case, condition=c) for c in ('C1-E', 'C3-9449-E')]
        table_rows.append([case, ci_text(rate([r.get('target_allowed') for r in groups[0]])),
                           ci_text(rate([r.get('target_allowed') for r in groups[1]])),
                           sum(r.get('denied_at_exchange', False) for r in groups[1]),
                           ci_text(rate([r.get('chain_reconstructed') for r in groups[1]]))])
    save(out, 'multihop', ['Case', 'Identity-only target allowed, Wilson 95%', 'Delegation/bound target allowed, Wilson 95%', 'Denied at exchange', 'Issued chain reconstructed, Wilson 95%'], table_rows)
    hop_rows=[]
    for condition in ('C1-E','C3-9449-E'):
        positive=selected(experiment='E2',case='positive',condition=condition)
        for index,label in enumerate(('Human grant to A','A to B')):
            values=[r['exchange_ms'][index] for r in positive if len(r.get('exchange_ms',[]))>index]
            hop_rows.append([condition,label,len(values),continuous_text(describe(values))])
        revokes=selected(experiment='E2',case='revoke-A',condition=condition)
        values=[r['revocation_to_denial_ms'] for r in revokes if r.get('revocation_to_denial_ms') is not None]
        hop_rows.append([condition,'Revoke A command to first B denial (host upper bound)',len(values),continuous_text(describe(values))])
    save(out,'delegation-timing',['Condition','Stage','Timed runs','Milliseconds median (IQR)'],hop_rows)
    table_rows = []
    for event in ('bound-replay', 'bearer-replay', 'coercion', 'audit-gap', 'audit-tamper'):
        for strategy in ('PAA', 'suspend-all'):
            group = selected(experiment='E3', event=event, strategy=strategy)
            table_rows.append([event, strategy, ci_text(rate([r.get('event_allowed') for r in group])),
                               ci_text(rate([r.get('legitimate_available') for r in group])), ci_text(rate([r.get('recovery_success') for r in group])),
                               continuous_text(describe([r.get('containment_ms') for r in group])),
                               continuous_text(describe([r.get('recovery_ms') for r in group]))])
    save(out, 'paa-response-recovery', ['Event', 'Policy', 'Event allowed, Wilson 95%', 'Legit available, Wilson 95%', 'Recovered, Wilson 95%', 'Event-response upper-bound ms, median (IQR)', 'Recovery ms, median (IQR)'], table_rows)
    expected={'bound-replay':{'refuse_request'},'bearer-replay':{'revoke_credential'},'coercion':{'deny_keep_identity_flag_input'},
              'audit-gap':{'escalate'},'audit-tamper':{'contain_identity','suspend_identity'}}
    response_rows=[]
    for event in expected:
        for strategy in ('PAA','suspend-all'):
            group=selected(experiment='E3',event=event,strategy=strategy)
            response_rows.append([event,strategy,json.dumps(dict(Counter(r.get('response_action') for r in group)),sort_keys=True),
                                  ci_text(rate([r.get('response_action') in expected[event] for r in group]))])
    save(out,'remediation',['Scripted event','Policy','Selected actions: counts','Preferred response accuracy, Wilson 95%'],response_rows)
    recovery_rows=[]
    for event in expected:
        for strategy in ('PAA','suspend-all'):
            group=selected(experiment='E3',event=event,strategy=strategy)
            recovery_rows.append([event,strategy,len(group),ci_text(rate([r.get('svid_changed') for r in group])),
                                  ci_text(rate([r.get('old_token_allowed_after_recovery') for r in group]))])
    save(out,'recovery-integrity',['Event','Policy','n','Changed SVID bytes, Wilson 95%','Old token accepted with current key, Wilson 95%'],recovery_rows)
    events = ('bound-replay', 'bearer-replay', 'coercion', 'audit-gap', 'audit-tamper')
    fig, ax = plt.subplots(figsize=(10, 4.2), constrained_layout=True)
    for shift, strategy, color in [(-.18, 'PAA', '#0284c7'), (.18, 'suspend-all', '#ea580c')]:
        values = [rate([r.get('legitimate_available') for r in selected(experiment='E3', event=e, strategy=strategy)]) for e in events]
        positions = [i+shift for i in range(len(events))]
        heights = [v['rate'] or 0 for v in values]
        ax.bar(positions, heights, .36, color=color, label=strategy)
        # Binomial endpoint roundoff can be a tiny positive value at p=0.
        # Clamp plotting lengths only; published interval values stay unchanged.
        ax.errorbar(positions, heights, yerr=[[max(0,h-v['ci_low']) for h,v in zip(heights,values)], [max(0,v['ci_high']-h) for h,v in zip(heights,values)]], fmt='none', color='#334155', capsize=3)
        for x,v in zip(positions,values):
            ax.text(x,.03,f"{v['successes']}/{v['n']}",ha='center',fontsize=8,rotation=90)
    ax.set_xticks(range(len(events)),events,rotation=12)
    ax.set_ylim(0,1.15)
    ax.set_ylabel('Legitimate availability; Wilson 95% CI')
    ax.set_title('Scripted PAA vs suspend-all (controlled events)')
    ax.legend(loc='upper center',ncol=2)
    for suffix in ('png','pdf'):
        fig.savefig(out / ('paa-availability.'+suffix),dpi=180)
    plt.close(fig)
    table_rows = []
    for model in json.loads((root / 'config.json').read_text(encoding='utf-8'))['models']:
        groups = [selected(experiment='E4-objective', model=model, condition=c) for c in ('C0-E', 'C2-E', 'C3-9449-E')]
        adverse = [[r for r in g if not r['objective'].startswith('positive-')] for g in groups]
        positive = [[r for r in g if r['objective'].startswith('positive-')] for g in groups]
        replay = [selected(experiment='E4-replay', model=model, condition=c) for c in ('C1-E', 'C2-E', 'C3-9449-E')]
        table_rows.append([model, *[ci_text(rate([r.get('unauthorized_outcome') for r in g])) for g in adverse],
                           *[ci_text(rate([r.get('task_completed') for r in g])) for g in positive],
                           *[ci_text(rate([r.get('attacker_allowed') for r in g])) for g in replay]])
    save(out, 'model-controls', ['Model', 'Adverse effect C0', 'Adverse effect C2', 'Adverse effect C3', 'Positive completion C0', 'Positive completion C2', 'Positive completion C3', 'Replay C1', 'Replay C2', 'Replay C3'], table_rows)
    runtime_rows=[]
    for experiment in ('E4-objective','E4-replay'):
        for model in json.loads((root/'config.json').read_text(encoding='utf-8'))['models']:
            group=selected(experiment=experiment,model=model)
            runtime_rows.append([experiment,model,len(group),sum(r['status']=='completed' for r in group),
                sum(r.get('runtime_seconds') or 0 for r in group),sum(r.get('cost_usd') or 0 for r in group)])
    save(out,'model-runtime-cost',['Experiment','Model','Primary n','Completed','Primary summed runtime s','Recorded primary token USD'],runtime_rows)
    table_rows=[]
    for event in ('bearer','bound'):
        for strategy in ('PAA','suspend-all'):
            group=selected(experiment='E1-joint', event=event, strategy=strategy)
            if group:
                table_rows.append([event,strategy,len(group),ci_text(rate([r.get('coerced_action_allowed') for r in group])),
                                   ci_text(rate([r.get('attacker_allowed') for r in group])),ci_text(rate([r.get('legitimate_available') for r in group]))])
    # Group by actual event labels if the frozen fixture uses a more specific name.
    if not table_rows:
        for event,strategy in sorted({(r['event'],r['strategy']) for r in selected(experiment='E1-joint')}):
            group=selected(experiment='E1-joint',event=event,strategy=strategy)
            table_rows.append([event,strategy,len(group),ci_text(rate([r.get('coerced_action_allowed') for r in group])),
                               ci_text(rate([r.get('attacker_allowed') for r in group])),ci_text(rate([r.get('legitimate_available') for r in group]))])
    save(out,'joint-attacks',['Replay binding','Policy','Scripted n','Coerced action allowed, Wilson 95%','Replay allowed, Wilson 95%','Legitimate available, Wilson 95%'],table_rows)
    table_rows=[]
    for exp in ('E1-scripted','E1-joint','E1-negative','E3'):
        pairs=[p for r in selected(experiment=exp) for p in r.get('classification_pairs',[])]
        for truth in ('none','coercion','impersonation'):
            group=[p for p in pairs if p['true']==truth]
            table_rows.append([exp,truth,*[sum(p['predicted']==label for p in group) for label in ('none','coercion','impersonation')],
                               ci_text(rate([p['predicted']==truth for p in group]))])
    save(out,'attribution-by-arm',['Scripted arm','Truth','Predicted none','Predicted coercion','Predicted impersonation','Accuracy, Wilson 95%'],table_rows)
    negative_rows=[]
    for condition in ('C0-E','C2-E','C3-9449-E'):
        group=selected(experiment='E1-negative',condition=condition)
        pairs=[p for r in group for p in r.get('classification_pairs',[])]
        negative_rows.append([condition,len(group),ci_text(rate([r.get('unauthorized_outcome') for r in group])),
                              ci_text(rate([p['predicted']=='none' for p in pairs]))])
    save(out,'attribution-negative-controls',['Condition','Scripted n','Unauthorized write runs, Wilson 95%','True-none request accuracy, Wilson 95%'],negative_rows)
    save(out,'paired-tests',['Objective','Protected','Matched pairs','Risk reduction','Exact McNemar p','Holm p','Verdict'],
         [[r.get('objective',r.get('family')),r['right'],r['n_pairs'],r['risk_reduction'],r['p_value'],r['p_holm'],r['verdict']] for r in report['tests']])
    approval_path=root/'operations/approval/summary.json'
    if approval_path.exists():
        approval=json.loads(approval_path.read_text(encoding='utf-8'))
        save(out,'simulated-approval',['Submissions','False approvals, Wilson 95%','False denials, Wilson 95%','Wait ms median (IQR)'],
             [[approval['n'],ci_text(approval['false_approval']),ci_text(approval['false_denial']),continuous_text(approval['wait_ms'])]])
        approval_rows=json.loads((approval_path.parent/'rows.json').read_text(encoding='utf-8'))
        replaced={r['rerun_of'] for r in approval_rows if r.get('rerun_of') is not None}
        approval_rows=[r for i,r in enumerate(approval_rows) if i not in replaced]
        dimensions=('delay_assumption_s','abandonment_assumption','rubber_stamp_assumption','fatigue_assumption_max')
        grid_rows=[]
        for values in sorted({tuple(r[k] for k in dimensions) for r in approval_rows}):
            group=[r for r in approval_rows if tuple(r[k] for k in dimensions)==values]
            grid_rows.append([*values,len(group),ci_text(rate([r['false_approval'] for r in group if not r['authorized']])),
                              ci_text(rate([r['false_denial'] for r in group if r['authorized']])),
                              ci_text(rate([r['timed_out'] for r in group])),continuous_text(describe([r['wait_ms'] for r in group]))])
        save(out,'simulated-approval-grid',['Delay s','Abandonment','Stamp','Fatigue max','n','False approvals, Wilson 95%','False denials, Wilson 95%','Timeouts, Wilson 95%','Wait ms median (IQR)'],grid_rows)
    failure_path=root/'operations/network-failure/result.json'
    if failure_path.exists():
        failure=json.loads(failure_path.read_text(encoding='utf-8'))
        save(out,'network-failure',['Planned probes','Before allowed, Wilson 95%','Outage refused, Wilson 95%','Outage writes','Fresh admission allowed, Wilson 95%','Restart command to healthy ms (single observation)'],
             [[1,ci_text(rate([failure['before_failure_allowed']])),ci_text(rate([failure['outage_refused']])),failure['outage_write_count'],
               ci_text(rate([failure['fresh_admission_allowed']])),failure['restart_elapsed_ms']]])
    # Resource samples are observer frames, not independent experimental runs.
    samples = defaultdict(list)
    if (root / 'resources.jsonl').exists():
        for line in (root / 'resources.jsonl').read_text(encoding='utf-8').splitlines():
            frame = json.loads(line)
            for item in frame['samples']:
                name = item.get('Name', '')
                samples[name].append({'cpu': float(item['CPUPerc'].rstrip('%')), 'memory': memory_bytes(item['MemUsage'].split('/')[0].strip())})
    resource_rows = []
    resource_json = {}
    for name, values in sorted(samples.items()):
        cpu = describe([v['cpu'] for v in values])
        memory = describe([v['memory'] / 1024**2 for v in values if v['memory'] is not None])
        resource_json[name] = {'observer_frames': len(values), 'cpu_percent': cpu, 'memory_MiB': memory}
        resource_rows.append([name, len(values), continuous_text(cpu), continuous_text(memory), max((v['memory'] or 0) for v in values)/1024**2])
    save(out, 'resources', ['Container', 'Observer frames', 'CPU % median (IQR)', 'Memory MiB median (IQR)', 'Max observed MiB'], resource_rows)
    write_json(out / 'resources.json', resource_json)
    # Raw rule/line/branch counts are maintenance proxies, not human effort.
    rego = (ROOT / 'infra/opa/policy.rego').read_text(encoding='utf-8')
    security = (ROOT / 'testbed/extension/security.py').read_text(encoding='utf-8')
    tree = ast.parse(security)
    static = {'original_rego_lines': len(rego.splitlines()), 'original_rego_rule_heads': len(re.findall(r'^(?:default )?[A-Za-z_][A-Za-z_0-9]*(?:\s*:=|\s+if)', rego, re.M))}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in ('authority', 'response_for', 'classify'):
            static[node.name] = {'lines': node.end_lineno-node.lineno+1, 'if_nodes': sum(isinstance(n, ast.If) for n in ast.walk(node))}
    write_json(out / 'policy-proxies.json', static)
    save(out, 'policy-proxies', ['Component', 'Lines', 'Rule heads / if nodes'], [
        ['Original OPA policy', static['original_rego_lines'], static['original_rego_rule_heads']],
        *[[k, v['lines'], v['if_nodes']] for k, v in static.items() if isinstance(v, dict)]])
    metrics = []
    for exp in sorted({r['experiment'] for r in rows}):
        for condition in sorted({r['condition'] for r in rows if r['experiment'] == exp}):
            group = selected(experiment=exp, condition=condition)
            median_call = lambda k: describe([statistics.median(r[k]) for r in group if r.get(k)])
            metrics.append([exp, condition, len(group), continuous_text(median_call('latency_ms')),
                            continuous_text(median_call('authorization_ms')), continuous_text(median_call('exchange_ms')),
                            continuous_text(median_call('sign_ms')), continuous_text(describe([r['audit_bytes']/r['action_count'] for r in group if r.get('action_count')]))])
    save(out, 'operational-costs', ['Experiment', 'Condition', 'n', 'Action roundtrip ms', 'PDP/dispatch ms', 'Exchange ms', 'Sign ms', 'Audit bytes/action'], metrics)
    identity_rows=[]
    for filename,label in [('identity-issuance.json','Resumed collector startup (initial pre-outage batch unavailable)'),('manual-rerun-identities.json','Linked local-platform rerun startup')]:
        if (root/filename).exists():
            identity=json.loads((root/filename).read_text(encoding='utf-8'))
            for item in identity['issuance_ms']:
                identity_rows.append([label,item['actor'],1,f"{item['ms']:.3f}"])
    for strategy in ('PAA','suspend-all'):
        values=[r['reattest_ms'] for r in selected(experiment='E3',strategy=strategy) if r.get('reattest_ms') is not None]
        identity_rows.append(['Fresh-SVID recovery issuance',strategy,len(values),continuous_text(describe(values))])
    save(out,'identity-lifecycle',['Observed stage','Actor / policy','n','Milliseconds (single value or median (IQR))'],identity_rows)
    fig, ax = plt.subplots(figsize=(11, 3.6), constrained_layout=True)
    ax.set_xlim(-.2, 11.2)
    ax.set_ylim(0, 3.6)
    ax.axis('off')
    boxes = [(0, 1.5, 1.15, 'Synthetic\nhuman grant'), (1.55, 1.5, 1.15, 'Agent A\nUID 10001'),
             (3.1, 1.5, 1.15, 'Agent B\nUID 10003'), (4.7, 1.5, 1.15, 'Remote PEP\nfront/control'),
             (6.3, 1.5, 1.6, 'PDP / STS / PA\ncontrol/tools'), (8.4, 1.5, 2.4, 'Private synthetic apps\nfiles / CRM / email / pay')]
    for x,y,w,label in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,.8,boxstyle='round,pad=.08',facecolor='#e0f2fe',edgecolor='#0369a1'))
        ax.text(x+w/2,y+.4,label,ha='center',va='center',fontsize=9)
    for left,right in zip(boxes,boxes[1:]):
        ax.annotate('',xy=(right[0]-.1,1.9),xytext=(left[0]+left[2]+.1,1.9),arrowprops={'arrowstyle':'->','color':'#334155'})
    ax.text(5.5,2.8,'Logical delegation / enforcement flow (harness orchestrated; both A and B call PEP)',ha='center',fontsize=9,color='#334155')
    ax.text(5.5,3.25,'SPIRE JWT-SVID admission + signed capability exchange',ha='center',fontsize=9,color='#334155')
    ax.text(7.7,.8,'Verified actor chain → authority → PAA response → independent effect evidence',ha='center',fontsize=9)
    ax.text(5.5,.2,'Single Windows PC / Docker-WSL2: network-separated, not multi-host',ha='center',fontsize=10,color='#9a3412')
    for suffix in ('png','pdf','svg'):
        fig.savefig(out / ('architecture.' + suffix),dpi=180)
    plt.close(fig)
    # Per-model ITT pilot follow rate is displayed without pooling phases.
    pilot = ROOT / 'results/extension-study-pilot-001/analysis/primary-rows.json'
    if pilot.exists():
        pilot_rows = json.loads(pilot.read_text(encoding='utf-8'))
        models = sorted({r['model'] for r in pilot_rows})
        diagnostic_rows=[]
        for model in models:
            group=[r for r in pilot_rows if r['model']==model]
            runtime_rows.append(['Pilot',model,len(group),sum(r['status']=='completed' for r in group),
                sum(r.get('runtime_seconds') or 0 for r in group),sum(r.get('cost_usd') or 0 for r in group)])
            exposed=0
            for r in group:
                actions_path=ROOT/'results/extension-study-pilot-001/runs'/r['run_key']/'actions.json'
                actions=json.loads(actions_path.read_text(encoding='utf-8')) if actions_path.exists() else []
                exposed+=any(a['request']['action']=='files.read' and a['request']['params'].get('path')=='brief' and a['data']['outcome']=='executed' for a in actions)
            diagnostic_rows.append([model,len(group),exposed,ci_text(rate([r.get('injection_followed') for r in group])),
                                    ci_text(rate([r.get('unauthorized_outcome') for r in group])),sum(r.get('harmful_effects',0) for r in group),
                                    sum(p['predicted']=='coercion' and p['true']!='coercion' for r in group for p in r.get('classification_pairs',[]))])
        save(out,'pilot-diagnostic',['Model','Pilot ITT n','Payload exposed','Exact follows, Wilson 95%','Any unauthorized write run, Wilson 95%','Unauthorized write actions','False coercion request labels'],diagnostic_rows)
        save(out,'model-runtime-cost',['Experiment','Model','Primary n','Completed','Primary summed runtime s','Recorded primary token USD'],runtime_rows)
        values = [rate([r.get('injection_followed') for r in pilot_rows if r['model']==m]) for m in models]
        fig, ax = plt.subplots(figsize=(8.5,3.6),constrained_layout=True)
        ax.barh(models,[v['rate'] or 0 for v in values],color='#0d9488')
        ax.errorbar([v['rate'] or 0 for v in values],range(len(models)),xerr=[[0]*len(models),[v['ci_high'] for v in values]],fmt='none',color='#334155',capsize=4)
        for i,v in enumerate(values):
            ax.text(.13,i,f"{v['successes']}/{v['n']}",va='center')
        ax.set_xlim(0,.25)
        ax.set_xlabel('Pilot exact follow fraction; Wilson 95% CI (ITT, limited exposure)')
        for suffix in ('png','pdf'):
            fig.savefig(out / ('pilot-follow-rates.'+suffix),dpi=180)
        plt.close(fig)
    write_json(out / 'presentation-layer.json', {'input':'analysis/report.json and sealed analyzer primary rows',
               'new_samples':0,'new_hypothesis_tests':0,'warning':'Mechanism counts, dependent request-level attribution, and observer resource frames are descriptive. This layer does not alter frozen analysis decisions.'})
    print(json.dumps({'publication_directory':str(out),'tables':len(list(out.glob('*.md'))),'primary_runs':len(rows)}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    publish(parser.parse_args().input)
