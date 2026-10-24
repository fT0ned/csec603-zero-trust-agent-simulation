"""Post-freeze presentation layer for final-study-001 (stdlib only, deterministic).

NOT part of the frozen file set: it recomputes nothing. It reads the outputs of the frozen analyzer
(analysis/final_study.py) and writes the paper package: evidence-class verdict wording, figures, null-result list.
Usage: python -m analysis.final_study_report --input results/final-study-001 --analysis results/final-study-001/analysis
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .binding_study import svg_bars

PALETTE = ['#0072b2', '#d55e00', '#009e73', '#cc79a7', '#e69f00', '#56b4e9', '#999999', '#000000']


def jread(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def crows(p):
    with Path(p).open(encoding='utf-8', newline='') as f:
        out = []
        for r in csv.DictReader(f):
            for k, v in list(r.items()):
                if isinstance(v, str) and v[:1] in '{[':
                    try: r[k] = json.loads(v)
                    except ValueError: pass
            out.append(r)
        return out


def frac(c): return '%d/%d' % (c['k'], c['n']) if c else 'n/a'


def mech_verdict(contrasts, hypothesis):
    cs = [c for c in contrasts if c['hypothesis'] == hypothesis and c['kind'] == 'confirmatory']
    met = [c for c in cs if c.get('practical_requirement_met')]
    measured = [c for c in cs if c.get('judgment') != 'Not measured']
    return {'contrasts': len(cs), 'measured': len(measured), 'threshold_met': len(met)}


def build(root, analysis):
    root, analysis = Path(root), Path(analysis)
    rep = jread(analysis / 'report.json'); assess = jread(analysis / 'part-a' / 'hypothesis-assessment.json')
    quality = jread(root / 'quality.json') if (root / 'quality.json').exists() else {}
    mech = crows(analysis / 'part-a-replay-mechanism.csv')
    cb = crows(analysis / 'part-b' / 'condition-results.csv')
    pc = jread(analysis / 'part-c' / 'results.json')
    contrasts = assess['contrasts']; eligible = assess['eligibility']['eligible']
    lines = ['# Paper package: final-study-001', '',
             'Everything here is measured in this single-machine testbed with the real model; see docs/final-study-protocol.md. This file only re-words the frozen analyzer outputs.', '',
             '## Collection', '']
    comp = rep['completeness']; cost = rep['cost_and_model']
    lines += ['- Planned runs: %s (total %d). Part A complete: %s; Part B complete: %s; Part C complete: %s.' % (rep['manifest_counts'], sum(rep['manifest_counts'].values()), comp['part_a_complete'], comp['part_b_complete'], comp['part_c_complete']),
              '- Raw seals verified: %s. Analysis errors: %d.' % (comp['raw_verified'], len(comp['errors'])),
              '- Host clock: steps over 0.5 s: %d; flagged runs: %d; timing replacements applied: %s.' % (len(quality.get('wall_clock_steps_over_0_5s', [])), len(quality.get('flagged_runs', [])), rep['timing_replacements']),
              '- Cost (computed): USD %.4f; returned model ids: %s; fingerprints: %s.' % (cost['total_cost_usd'], cost['returned_model_ids'], list(cost['system_fingerprints'])), '',
              '## Hypothesis verdicts (evidence class first)', '',
              'Support claims need the frozen, complete collection (eligible: **%s**). Configuration-determined rows are mechanism verification: threshold counts, no p-value claim.' % eligible, '',
              '| Hypothesis | Evidence class | Result |', '|---|---|---|']
    for h in ('H1', 'H1b', 'H3'):
        m = mech_verdict(contrasts, h)
        lines.append('| %s | mechanism verification | threshold met in %d of %d measured planned contrasts (%d defined) |' % (h, m['threshold_met'], m['measured'], m['contrasts']))
    for h in ('H2', 'H2b', 'H2c'):
        cs = [c for c in contrasts if c['hypothesis'] == h and c['kind'] == 'confirmatory']
        sup = [c for c in cs if c['judgment'].startswith('Supported')]
        lines.append('| %s | measured behaviour (left side) | Holm and threshold both met in %d of %d contrasts; the rest are null or below threshold (listed under Null results) |' % (h, len(sup), len(cs)))
    lines.append('| H3b | mechanism verification | %s |' % next(v['verdict'] for v in rep['verdicts'] if v['hypothesis'] == 'H3b'))
    lines.append('| H4 | descriptive | see latency-overhead-approval.md |')
    for v in rep['verdicts']:
        if v['hypothesis'] in ('A1', 'A2', 'A3', 'B1', 'B2'): lines.append('| %s | %s | %s |' % (v['hypothesis'], v['evidence_class'], v['verdict']))
    nulls = []
    for c in contrasts:
        if c['kind'] == 'confirmatory' and c['judgment'] not in ('Supported in this testbed', 'Not measured') and c['hypothesis'] in ('H2', 'H2b', 'H2c'):
            nulls.append('%s %s %s %s->%s p_holm=%s' % (c['hypothesis'], c['scenario'], c['metric'], c['left'], c['right'], c.get('p_holm')))
    lines += ['', '## Null or non-supported contrasts (stated plainly)', '', *(['- ' + n for n in sorted(nulls)] or ['- none']), '']
    s2 = [r for r in crows(analysis / 'injection-follow-rate.csv')]
    lines += ['Injection follow rates (separate from committed harm): ' + '; '.join('%s %s %s' % (r['scenario'], r['condition'], r['injection_followed']) for r in s2), '',
              '## Threats to validity', '',
              '- One mutable model alias, one host, synthetic tools, simulated approver, scripted thief; no production inference.',
              '- Temperature 0 makes repeats near-deterministic: effective sample size is closer to the number of distinct fixtures than to 30.',
              '- C2-AS/C3/C3-AS are identical to C2 in S2/S5 by construction, so not allocated there.',
              '- Part A S3/S4 timing resolution: 10 s (S3) and 0.1 s (S4) probe grids; exposure for C0 is right-censored at the window end.',
              '- Stages ran B and C first, then A, so Part A timing is not perturbed by other parts, but the stages are not interleaved in time.', '']
    (analysis / 'paper-package.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    # figures
    items = []
    for m in mech:
        if m['scenario'] == 'S3' and str(m['ttl_seconds']) == '900':
            items.append((m['condition'], round(m['exposure_seconds']['median'] or 0, 1), PALETTE[len(items) % 8]))
    if items: svg_bars(analysis / 'fig-s3-exposure-ttl900.svg', 'S3 stolen-token exposure, TTL 900 s (median seconds)', items, ' s')
    avail = [(c, round(100 * (v['legit_after_attack_allowed']['n'] - v['legit_after_attack_allowed']['k']) / max(1, v['completed']), 1), PALETTE[i % 8]) for i, (c, v) in enumerate(pc['conditions'].items())]
    svg_bars(analysis / 'fig-part-c-lockout.svg', 'Part C: legitimate agent refused right after the attack (%)', avail, '%', 100)
    rates = []
    for r in cb:
        if r['scenario'] in ('scope-delete', 'workflow-export', 'approval-payment', 'principal-vendor'):
            p = r['any_unauthorized_commit']; rates.append(('%s %s' % (r['scenario'][:12], r['condition']), round(100 * (p['rate'] or 0), 1), PALETTE[len(rates) % 8]))
    if rates: svg_bars(analysis / 'fig-part-b-unauthorized.svg', 'Part B: runs with an unauthorized commit (%)', rates, '%', 100)
    return {'paper_package': str(analysis / 'paper-package.md'), 'nulls': len(nulls)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True); p.add_argument('--analysis', required=True)
    a = p.parse_args(argv)
    print(json.dumps(build(a.input, a.analysis)))
    return 0


if __name__ == '__main__': raise SystemExit(main())
