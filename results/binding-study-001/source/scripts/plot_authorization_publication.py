"""Presentation-only workflow layout derivative; preserve all frozen plot outputs."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.plot_authorization_study import COLORS
from testbed.common import ROOT


def main():
    batch = ROOT/'results/agent-authorization-study-001'; out = batch/'figures'
    report = json.loads((batch/'analysis/report.json').read_text(encoding='utf-8'))
    assert report['validation_passed'] and report['confirmatory_eligible']
    original = out/'figure-manifest.json'; preserved = out/'figure-manifest-original.json'
    if preserved.exists(): raise ValueError('Publication derivative already prepared')
    preserved.write_bytes(original.read_bytes())
    manifest = json.loads(original.read_text(encoding='utf-8'))
    rows = sorted([r for r in report['tables'] if r['scenario']=='workflow-export'], key=lambda r:list(COLORS).index(r['condition']))
    fig, ax = plt.subplots(figsize=(6.4,3.7))
    for i, row in enumerate(rows):
        d = row['committed_records']; value = d['median']
        ax.bar(i,value,color=COLORS[row['condition']],width=.65)
        ax.errorbar(i,value,yerr=[[value-d['q1']],[d['q3']-value]],fmt='none',ecolor='black',capsize=5)
        ax.text(i,value+.5,f'{value:g}',ha='center')
    ax.axhline(10,linestyle='--',color='#a1392e',label='Trusted principal limit = 10')
    ax.set_xticks(range(len(rows)),[r['condition'] for r in rows]);ax.set_ylim(0,23)
    ax.set_ylabel('Independently committed exported records')
    ax.set_title('Confirmatory real-LLM study\nWorkflow export median and interquartile range')
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.15),frameon=False);fig.tight_layout()
    for ext in ('png','svg','pdf'):
        path=out/('workflow-export-publication.'+ext)
        metadata={'Date':None} if ext=='svg' else {'CreationDate':None,'ModDate':None} if ext=='pdf' else {}
        fig.savefig(path,dpi=180,metadata=metadata,bbox_inches='tight')
        manifest['exports'][path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    plt.close(fig)
    manifest['exports'][preserved.name]=hashlib.sha256(preserved.read_bytes()).hexdigest()
    manifest['publication_note']='Presentation-only derivative moves workflow legend below axes; original six plot files and original manifest remain unchanged/preserved. No data or statistical changes.'
    original.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'publication_derivative':True,'original_plot_files_preserved':6}))


if __name__=='__main__': main()
