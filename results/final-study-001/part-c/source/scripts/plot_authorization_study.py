"""Export paper figures from one validated authorization study, without pooling."""
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COLORS = {'C0': '#626b73', 'C1': '#346ba8', 'C2': '#1c7a56', 'C2-noWF': '#8958a3', 'C2-RS': '#bc611d'}
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
                     'pdf.fonttype': 42, 'svg.hashsalt': 'csec603-authorization-v1',
                     'axes.spines.top': False, 'axes.spines.right': False})


def export(report_path, output):
    report_path = Path(report_path); output = Path(output)
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if not report['validation_passed']: raise ValueError('Do not plot unvalidated findings as accepted results')
    output.mkdir(parents=True, exist_ok=False)
    label = 'Confirmatory real-LLM study' if report['confirmatory_eligible'] else 'Exploratory real-LLM pilot'
    tables = report['tables']; exports = {}
    def save(fig, name):
        fig.tight_layout()
        for ext in ('png', 'svg', 'pdf'):
            path = output/(name+'.'+ext)
            metadata = {'Date': None} if ext == 'svg' else {'CreationDate': None, 'ModDate': None} if ext == 'pdf' else {}
            fig.savefig(path, dpi=180, metadata=metadata, bbox_inches='tight')
            exports[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(9, 6), sharey=True)
    for ax, scenario in zip(axes.flat, ('scope-delete', 'principal-vendor', 'workflow-export', 'approval-payment')):
        rows = [r for r in tables if r['scenario'] == scenario]
        rows.sort(key=lambda r: list(COLORS).index(r['condition']))
        for i, row in enumerate(rows):
            interval = row['any_unauthorized_commit']; value = interval['rate']
            ax.bar(i, value, color=COLORS[row['condition']], width=.65)
            ax.errorbar(i, value, yerr=[[max(0, value-interval['ci_low'])], [max(0, interval['ci_high']-value)]],
                        fmt='none', ecolor='black', capsize=4, lw=1)
            ax.text(i, min(1.16, value+.13), f"{interval['successes']}/{interval['n']}", ha='center', fontsize=8)
        ax.set_xticks(range(len(rows)), [r['condition'] for r in rows])
        ax.set_ylim(0, 1.22); ax.set_title(scenario.replace('-', ' ')); ax.set_yticks([0, .25, .5, .75, 1])
        ax.set_ylabel('Runs with unauthorized committed effect')
    fig.suptitle(label+'\nIndependent tool state; Wilson 95% intervals', fontsize=11)
    save(fig, 'unauthorized-commit-risk')
    fig, ax = plt.subplots(figsize=(6.4, 3.7))
    rows = sorted([r for r in tables if r['scenario'] == 'workflow-export'], key=lambda r: list(COLORS).index(r['condition']))
    for i, row in enumerate(rows):
        d = row['committed_records']; median = d['median']
        ax.bar(i, median, color=COLORS[row['condition']], width=.65)
        ax.errorbar(i, median, yerr=[[median-d['q1']], [d['q3']-median]], fmt='none', ecolor='black', capsize=5)
        ax.text(i, median+.5, f"{median:g}", ha='center')
    ax.axhline(10, linestyle='--', color='#a1392e', label='Trusted principal limit = 10')
    ax.set_xticks(range(len(rows)), [r['condition'] for r in rows]); ax.set_ylim(0, 23)
    ax.set_ylabel('Independently committed exported records'); ax.legend(loc='upper left')
    ax.set_title(label+'\nWorkflow export median and interquartile range')
    save(fig, 'workflow-export-records')
    (output/'figure-manifest.json').write_text(json.dumps({'classification': label,
        'report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(), 'exports': exports,
        'captions': {'unauthorized-commit-risk': 'Authors’ work. Run-level unauthorized mutating effects independently reconciled against tool state. Wilson 95% intervals describe each condition; calls are not independent replicates.',
                     'workflow-export-records': 'Authors’ work. Independent exported-record totals per run, median and interquartile range. The dashed line is the separately trusted ten-record authorization, not the twenty-record agent objective.'}}, indent=2)+'\n', encoding='utf-8')
    return {'files': len(exports), 'classification': label}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--report', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(); print(json.dumps(export(args.report, args.output)))


if __name__ == '__main__': main()
