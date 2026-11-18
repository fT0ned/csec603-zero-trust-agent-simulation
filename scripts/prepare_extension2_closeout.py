"""Wait for collection/analysis, then validate and prepare archival documentation.

No model calls or publication. Human-facing artifact review and the already
authorized release are performed by the research agent after this preparation.
"""
import json
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from analysis.study002 import rate
from testbed.common import ROOT,write_json


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def checked(command,name):
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    (ROOT/f'.runtime/extension2/closeout-{name}.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError('Postcollection '+name+' failed; inspect private log')


def main():
    status=ROOT/'.runtime/extension2/guardian-status.json'
    while True:
        state=read(status)
        if state['stage']=='analysis-closeout-report-ready':break
        if 'inspection-required' in state['stage']:raise RuntimeError('Guardian requires engineering inspection; no publication')
        time.sleep(30)
    checked([sys.executable,'-m','scripts.describe_extension2_host'],'host')
    test_path=ROOT/'docs/verification/study002-final-tests.xml'
    checked([sys.executable,'-m','pytest','-q','-o','addopts=','--junitxml='+str(test_path)],'tests')
    suites=list(ET.parse(test_path).getroot().iter('testsuite'))
    tests={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    if tests['failures'] or tests['errors'] or tests['skipped'] or tests['tests']<236:raise RuntimeError('Final suite failed, skipped or unexpectedly missing tests')
    checked([sys.executable,'-m','scripts.closeout_extension2'],'preservation-accounting')
    checked([sys.executable,'-m','analysis.study002_report'],'report')
    folder=ROOT/'results/extension-study-002'
    report=read(folder/'analysis/report.json');close=read(ROOT/'docs/extension-study-002-closeout.json')
    rows=read(folder/'analysis/primary-rows.json')
    # Public overview reports exact observed counts, without stronger claims.
    c0=[r for r in rows if r['experiment']=='E5' and r['family']!='benign' and r['condition']=='C0-002']
    harm=rate([r.get('committed_harm') for r in c0]);attempts=rate([r.get('coerced_write') for r in c0])
    protected=[r for r in rows if r['experiment']=='E5' and r['family']!='benign' and r['condition']!='C0-002']
    ph=rate([r.get('committed_harm') for r in protected])
    marker='## Guaranteed-exposure follow-up (study002)'
    body=f'''{marker}

The [protocol](docs/extension-study-002-protocol.md) and [completion report](docs/extension-study-002-completion-report.md) preserve the prior limited-exposure null unchanged. This additive follow-up completed240 fixed pilot units,5,040 full real-model E5 units,600 planned real-model/scripted-thief joint opportunities and240 scripted attenuation units. The full archive has{report['coverage']['primary']}primary/{report['coverage']['raw']}raw units; all{close['protected_paths_unchanged']:,}protected original/001 paths are unchanged;{tests['tests']-tests['failures']-tests['errors']-tests['skipped']}tests pass.

Full injected C0 baseline: coerced attempts{attempts['successes']}/{attempts['n']}; committed harm{harm['successes']}/{harm['n']}. Combined protected conditions committed{ph['successes']}/{ph['n']}coerced harms; per-condition counts, task completion, exposure, exact McNemar/Holm verdicts, attribution errors, confidence intervals and all nulls are in the report. These are synthetic controlled tasks, not general model rankings or production assurances. C3 includes authority enforcement and remains an experimental proof-of-possession profile. Stock Llama/Mistral pilot interfaces failed benign calibration; same-weight rendering fixes were disclosed before full freeze, without extra sampling or changed eligibility. The original pilot is not pooled with full collection.

One-command sealed reanalysis (source/evidence ZIP or checkout):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/reproduce_extension2.ps1
```

Fresh collection requires a Git checkout with the pushed`extension-study-002-freeze-v1`tag, ignored`.env`, Docker/NVIDIA, network access and the preserved`.runtime/spend.sqlite`ledger. Never reset that ledger to obtain a new budget:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/reproduce_extension2.ps1 -Mode Collect
```

[Markdown/LaTeX tables and figures](results/extension-study-002/publication), [pilot results](results/extension-study-002-pilot/analysis), [template amendment](docs/extension-study-002-amendments.md), [archive release](https://github.com/fT0ned/csec603-zero-trust-agent-simulation/releases/tag/extension-study-002), and [owner DOI steps](docs/extension-zenodo-steps.md). Global conservative ledgerUSD{close['global_ledger_charged_usd']:.9f}; study002USD{close['study002_ledger_charged_usd']:.9f}. The paper was not edited.
'''
    path=ROOT/'README.md';original=path.read_text(encoding='utf-8')
    prefix=original.split(marker)[0].rstrip();path.write_text(prefix+'\n\n'+body.rstrip()+'\n',encoding='utf-8')
    checklist=ROOT/'docs/extension-study-002-definition-of-done.md'
    value=checklist.read_text(encoding='utf-8')
    for phrase in ('Full30','E6 strict','Exact counts','Complete final suite','Markdown/LaTeX'):
        value=value.replace('- [ ] '+phrase,'- [x] '+phrase)
    checklist.write_text(value,encoding='utf-8')
    progress=ROOT/'docs/extension-study-002-progress.md'
    with progress.open('a',encoding='utf-8') as stream:
        stream.write(f"\n\nCOLLECTION/ANALYSIS/VALIDATION COMPLETE: primary{report['coverage']['primary']}, raw{report['coverage']['raw']}; final suite{tests}; protected paths{close['protected_paths_unchanged']:,}unchanged. Report/publication tables generated. Awaiting agent figure review, archive commit/tag/push, decompressed secret scan and verified GitHub release. No additional model calls.\n")
    portable={p.name:sorted({c for c in p.read_text(encoding='utf-8') if ord(c)>127}) for p in (folder/'publication').glob('*.tex')}
    write_json(ROOT/'docs/extension-study-002-final-validation.json',{'checked_at':time.time(),'tests':tests,
        'coverage':report['coverage'],'protected_paths_unchanged':close['protected_paths_unchanged'],
        'portable_tex_remaining_nonascii':{k:v for k,v in portable.items() if v},
        'publication_status':'Prepared; agent figure review and release verification pending'})
    write_json(ROOT/'.runtime/extension2/closeout-status.json',{'stage':'prepared-for-agent-artifact-review','updated_at':time.time(),'tests':tests})
    print('Study002 prepared for agent artifact review; no publication performed.',flush=True)


if __name__=='__main__':main()
