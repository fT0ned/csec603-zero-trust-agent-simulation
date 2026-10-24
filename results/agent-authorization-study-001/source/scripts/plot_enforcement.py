"""Postcollection descriptive figures; no raw mutation, pooling or hypothesis tests.

python scripts/plot_enforcement.py --report results/COHORT/enforcement/report.json --output results/COHORT/figures
Repeat --report to export multiple collections in separate figures and tables.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COLORS={'C0':'#5b6470','C1':'#2768ad','C2':'#15835a','C2-noWF':'#8456a3','C2-RS':'#c46819'}
ORDER={name:i for i,name in enumerate(COLORS)}
plt.rcParams.update({'svg.hashsalt':'csec603-descriptive-enforcement-v1','font.family':'DejaVu Sans',
                     'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def csv_write(path,rows):
    fields=list(dict.fromkeys(k for row in rows for k in row)) or ['No measured rows']
    with path.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)

def export(report_paths,output):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=True)
    source_hashes={};tables=[];metric_rows=[];created=[];seen=set()
    for report_path in report_paths:
        path=Path(report_path).resolve();report=json.loads(path.read_text(encoding='utf-8'))
        if report.get('no_inferential_claims') is not True:raise ValueError('Select the separate descriptive enforcement report')
        if report.get('errors'):raise ValueError('Resolve report evidence errors before plotting')
        collection=report['collection_id']
        if collection in seen:raise ValueError('Duplicate collection report; refusing accidental pooling/overwrite')
        seen.add(collection);source_hashes[str(path)]=sha(path)
        prefix=re.sub(r'[^A-Za-z0-9._-]','_',collection)
        groups=report['groups'];modes={g['mode'] for g in groups}
        label='EXPLORATORY REAL-LLM PILOT' if modes=={'llm'} else 'SCRIPTED ENGINEERING CHECK' if modes=={'scripted'} else 'SEPARATE MODES - DESCRIPTIVE ONLY'
        for group in groups:
            group_label='EXPLORATORY REAL-LLM PILOT' if group['mode']=='llm' else 'SCRIPTED ENGINEERING CHECK' if group['mode']=='scripted' else 'DESCRIPTIVE ONLY'
            identifiers={k:group.get(k) for k in ['collection_id','mode','phase','model','system_prompt_profile','system_prompt_sha256','protocol_id','study_kind','condition','scenario','payload_id','approval_dependent','ttl_seconds','revocation_mode']}
            for endpoint in ['unauthorized_outcome','supplemental_intent_violation']:
                stats=group[endpoint]
                tables.append({**identifiers,'endpoint':endpoint,**stats,'evidence_class':group_label})
            for key,value in group.items():
                if isinstance(value,dict) and 'median' in value:
                    metric_rows.append({**identifiers,'metric':key,**value,
                        'unit':'ms' if key.endswith('_ms') else 'ratio' if key=='cumulative_ratio' else 'records' if key=='cumulative_total' and group.get('cumulative_unit')=='records' else 'payment units' if key=='cumulative_total' else 'count',
                        'evidence_class':group_label})
        # Figures never combine distinct cohorts or modes. Even within a cohort,
        # different models/prompts remain separate labeled points.
        for mode in sorted(modes,key=str):
            panel_label='EXPLORATORY REAL-LLM PILOT' if mode=='llm' else 'SCRIPTED ENGINEERING CHECK' if mode=='scripted' else 'DESCRIPTIVE ONLY'
            for scenario in sorted({g['scenario'] for g in groups if g['mode']==mode}):
                selected=sorted([g for g in groups if g['mode']==mode and g['scenario']==scenario],key=lambda g:(g.get('payload_id') or '',ORDER.get(g['condition'],99),str(g.get('model')),str(g.get('system_prompt_profile'))))
                endpoints=['unauthorized_outcome']+(['supplemental_intent_violation'] if scenario=='S5' else [])
                fig,axes=plt.subplots(1,len(endpoints),figsize=(7.5*len(endpoints),max(3.5,.35*len(selected)+2)),squeeze=False,sharey=True)
                ylabels=[f'{g["condition"]} | {g.get("payload_id") or "normal work"}' for g in selected]
                mixed=len({(g.get('model'),g.get('system_prompt_profile'),g.get('ttl_seconds'),g.get('revocation_mode')) for g in selected})>1
                if mixed:ylabels=[f'{text} | {g.get("model")} | {g.get("system_prompt_profile")} | TTL{g.get("ttl_seconds")} | {g.get("revocation_mode")}' for text,g in zip(ylabels,selected)]
                for ax,endpoint in zip(axes[0],endpoints):
                    for y,g in enumerate(selected):
                        value=g[endpoint];color=COLORS.get(g['condition'],'black')
                        if value['rate'] is None:
                            ax.text(.45,y,'Not measured (n=0)',va='center',color='#666666')
                        else:
                            rate=value['rate'];low=value['ci_low'];high=value['ci_high']
                            ax.errorbar(rate,y,xerr=[[max(0,rate-low)],[max(0,high-rate)]],fmt='o',color=color,capsize=3,markersize=5)
                            ax.text(1.025,y,f'{value["successes"]}/{value["n"]}',va='center',fontsize=8,clip_on=False)
                    ax.set_xlim(-.025,1.0);ax.set_ylim(len(selected)-.5,-.5)
                    ax.set_yticks(range(len(selected)),ylabels)
                    ax.set_xticks([0,.25,.5,.75,1],['0%','25%','50%','75%','100%'])
                    ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
                    ax.set_xlabel('Per-run rate; Wilson 95% interval')
                    title='Primary unauthorized outcome' if endpoint=='unauthorized_outcome' else 'Supplemental intent violation (any harmful commit)'
                    if scenario=='S1':title='S1 legitimate-control unauthorized endpoint (not an attack)'
                    ax.set_title(title,fontsize=10)
                profiles=', '.join(sorted({str(g.get('system_prompt_profile')) for g in selected}));models=', '.join(sorted({str(g.get('model')) for g in selected}))
                fig.suptitle(f'{panel_label}\n{collection} | {scenario} | {mode} | {models} | {profiles}',fontsize=11)
                fig.text(.01,.01,'Fixed author-selected workload; no original-study pooling or hypothesis-support claim. k/n labels are run counts, not calls.',fontsize=8)
                fig.tight_layout(rect=(0,.04,.97,.91))
                stem=f'{prefix}-{mode}-{scenario}-rates'
                for extension in ['svg','pdf','png']:
                    destination=out/f'{stem}.{extension}'
                    metadata={'Date':None} if extension=='svg' else {'CreationDate':None,'ModDate':None} if extension=='pdf' else {'Software':'matplotlib '+matplotlib.__version__}
                    fig.savefig(destination,dpi=180,bbox_inches='tight',metadata=metadata);created.append(destination)
                plt.close(fig)
    csv_write(out/'endpoint-rates.csv',tables);csv_write(out/'descriptive-run-metrics.csv',metric_rows)
    csv_write(out/'cohort-labels.csv',[{'collection_id':x,'evidence':'Separate collection; see report and point labels'} for x in sorted(seen)])
    (out/'README.md').write_text('# Descriptive enforcement figures\n\nEach collection/mode/scenario has separate SVG/PDF/PNG exports. Rates and Wilson intervals are copied from the independently reconciled descriptive report without pooling or reanalysis. S5 supplemental intent is separate from primary chained-total success; Not measured means no endpoint observations, not zero.\n\n`endpoint-rates.csv` retains full stratum identifiers, numerators, denominators and intervals. `descriptive-run-metrics.csv` preserves distributions of within-run median/p95 action and authorization times, workflow ratios/totals, reachable authority and approval burden. These distributions are not call-level independent observations. `figure-manifest.json` pins the consumed reports, plotting script and exported artifacts.\n\nLLM pilot figures are exploratory; scripted figures are engineering checks and cannot be presented as measured natural model susceptibility. Raw data and original study reports remain separate.\n',encoding='utf-8')
    manifest={'kind':'Postcollection descriptive exports; no hypothesis tests','matplotlib_version':matplotlib.__version__,
              'script_sha256':sha(Path(__file__)),'report_hashes':source_hashes,
              'exports':{p.name:sha(p) for p in created+[out/'endpoint-rates.csv',out/'descriptive-run-metrics.csv',out/'cohort-labels.csv',out/'README.md']}}
    (out/'figure-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',action='append',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args(argv);manifest=export(args.report,args.output)
    print(json.dumps({'collections':len(manifest['report_hashes']),'exported_artifacts':len(manifest['exports'])}))

if __name__=='__main__':main()
