"""Combined, deterministic, offline analysis of final-study-001 (stdlib only).

Usage: python -m analysis.final_study --input results/final-study-001 --output results/final-study-001/analysis

Reuses the per-part analyzers (analysis.run for Part A, analysis.authorization_study for Part B,
analysis.binding_study for Part C), applies the prespecified timing-rerun replacement rule, and writes one paper package.
Never calls a provider and never modifies raw data.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from . import authorization_study as auth
from . import binding_study as bind
from . import hypotheses as hyp
from . import run as core
from .cli import verify_raw
from .statistics import describe, wilson

PARTS = {'A': 'part-a', 'B': 'part-b', 'C': 'part-c'}
ROOT = Path(__file__).resolve().parents[1]
CLASS = {'mech': 'mechanism verification (configuration-determined; counts + Wilson CI, no p-value claim)',
         'meas': 'measured behaviour (outcome can vary with model behaviour)',
         'desc': 'descriptive'}


def jread(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def jlines(path):
    p = Path(path)
    return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x] if p.exists() else []


def digest(x): return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def ci(k, n):
    w = wilson(k, n)
    return {'k': k, 'n': n, 'rate': w['rate'], 'lo': w['ci_low'], 'hi': w['ci_high']}


def pct(c):
    return 'n/a' if not c['n'] else '%d/%d (%.1f%%; 95%% CI %.1f-%.1f%%)' % (c['k'], c['n'], 100 * c['rate'], 100 * c['lo'], 100 * c['hi'])


def num(d, key='median', digits=2):
    v = d.get(key) if d else None
    return 'n/a' if v is None else ('%.' + str(digits) + 'f') % v


def iqr(d):
    return 'n/a' if not d or d.get('median') is None else '%.2f (IQR %.2f-%.2f)' % (d['median'], d['q1'], d['q3'])


def md_table(headers, rows):
    out = ['| ' + ' | '.join(headers) + ' |', '|' + '|'.join('---' for _ in headers) + '|']
    out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return '\n'.join(out) + '\n'


def write_csv(path, rows, fields=None):
    fields = fields or list(dict.fromkeys(k for r in rows for k in r)) or ['none']
    with Path(path).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader()
        for r in rows: w.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v for k, v in r.items()})


# ------------------------------------------------------------------ loading and replacement rule
def summaries(folder):
    return [jread(p) for p in sorted((Path(folder) / 'runs').glob('*/summary.json'))]


def timing_replacements(root):
    """{part: {original_run_id: rerun_run_id}} for completed prespecified timing reruns."""
    out = {p: {} for p in PARTS}
    for part, name in PARTS.items():
        for s in summaries(Path(root) / name):
            if 'timing_rerun_of' in s and s.get('status') in ('completed', 'model_step_limit', 'provider_failure'):
                out[part][s['timing_rerun_of']] = s['run_id']
    return out


def patch_core(root, replaced):
    original = core.load_runs
    rerun_ids = set(replaced.values())

    def loader(path):
        records, sources, errors = original(path)
        for r in records:
            if r.get('run_id') in replaced:
                r['analysis_excluded_reason'] = 'Prespecified timing rerun used (host clock-step flag); original retained for sensitivity'
                r['analysis_canonical_run_id'] = replaced[r['run_id']]
            elif r.get('run_id') in rerun_ids:
                r.pop('analysis_excluded_reason', None); r.pop('analysis_canonical_run_id', None)
        return records, sources, errors
    core.load_runs = loader
    return original


def eligibility_factory(root, replaced_all, quality):
    root = Path(root)

    def elig(part_root, records):
        checks = {}
        config = jread(root / 'config.json'); freeze = jread(root / 'freeze.json') if (root / 'freeze.json').exists() else {}
        manifest = jread(root / 'final-manifest.json')
        checks['genuine_full_phase'] = config.get('phase') == 'full' and config.get('mode') == 'llm'
        checks['frozen_config_matches'] = freeze.get('status') == 'frozen' and freeze.get('config_sha256') == digest(config)
        tag = freeze.get('tag')
        ancestor = subprocess.run(['git', 'merge-base', '--is-ancestor', tag or 'none', manifest.get('git_commit', 'none')], cwd=ROOT, capture_output=True).returncode == 0
        checks['freeze_precedes_collection'] = ancestor
        expected = Counter(manifest['cells']['A'])
        finished = Counter(core_uid(r) for r in records if core.eligible_record(r))
        checks['all_planned_units_completed_once'] = finished == expected
        checks['real_models_reported'] = bool(records) and all(r.get('model_snapshots') for r in records if core.eligible_record(r))
        checks['raw_files_verified'] = all(verify_raw(root / n)['valid'] for n in PARTS.values())
        checks['clock_flags_resolved'] = not quality.get('flagged_timing_runs_without_rerun')
        failed = [k for k, v in checks.items() if not v]
        return {'eligible': not failed, 'checks': checks, 'failed_checks': failed, 'planned_units': sum(expected.values()),
                'finished_units': sum(finished.values()), 'required_units': sum(expected.values()),
                'note': 'Final-study eligibility: frozen config, tagged freeze before collection, complete planned matrix, sealed raw files, resolved clock flags.'}
    return elig


def core_uid(r):
    return json.dumps([r['condition'], r['scenario'], r['ttl_seconds'], r['revocation_mode'], r['seed']], sort_keys=True, separators=(',', ':'), ensure_ascii=False)


# ------------------------------------------------------------------ Part A supplementary tables
def part_a_rows(records):
    return [r for r in records if core.eligible_record(r)]


def replay_mechanism(records):
    """Per (scenario, condition, ttl, mode): observed events, exposure, first-probe reasons, availability. Counts, no tests."""
    groups = defaultdict(list)
    for r in part_a_rows(records):
        if r['scenario'] in ('S3', 'S4'): groups[(r['scenario'], r['condition'], r['ttl_seconds'], r['revocation_mode'])].append(r)
    rows = []
    for (sc, cond, ttl, mode), runs in sorted(groups.items(), key=lambda x: str(x[0])):
        n = len(runs); ev = [r for r in runs if r.get('event_observed') is True]
        exposure = [r['last_success_seconds'] if 'last_success_seconds' in r else r.get('exposure_seconds') for r in runs if isinstance(r.get('exposure_seconds', r.get('last_success_seconds')), (int, float))]
        den = [r['first_denial_seconds'] for r in ev if isinstance(r.get('first_denial_seconds'), (int, float))]
        avail = [r for r in runs if 'legit_after_attack_allowed' in r]
        rows.append({'scenario': sc, 'condition': cond, 'ttl_seconds': ttl, 'revocation_mode': mode, 'runs': n,
                     'event_observed': ci(len(ev), n), 'right_censored': n - len(ev),
                     'exposure_seconds': describe(exposure), 'first_denial_seconds': describe(den),
                     'harmful_executed_runs': ci(sum(bool(r.get('harmful_executed')) for r in runs), n),
                     'reachable_authority': describe([r['reachable_authority'] for r in runs if isinstance(r.get('reachable_authority'), (int, float))]),
                     'first_attacker_request_reasons': dict(Counter(r.get('first_attacker_request_reason') for r in runs if r.get('first_attacker_request_reason'))),
                     'first_attacker_probe_reasons': dict(Counter(r.get('first_attacker_probe_reason') for r in runs if r.get('first_attacker_probe_reason'))),
                     'legit_available_after_attack': ci(sum(bool(r['legit_after_attack_allowed']) for r in avail), len(avail)) if avail else None,
                     'revocation_moot_runs': sum(bool(r.get('revocation_moot')) for r in runs),
                     'revocation_propagation_ms': describe([r['revocation_propagation_ms'] for r in runs if isinstance(r.get('revocation_propagation_ms'), (int, float))]),
                     'theft_schedule_error_abs_max_s': max([abs(r['theft_schedule_error_seconds']) for r in runs if isinstance(r.get('theft_schedule_error_seconds'), (int, float))], default=None)})
    return rows


def cost_and_model(records_a, rows_b, runs_c):
    out = {}
    models, prints = Counter(), Counter()
    for part, rs in (('A', records_a), ('B', rows_b), ('C', runs_c)):
        cost = 0.0; n = 0; tokens = {'prompt_tokens': 0, 'completion_tokens': 0}
        for r in rs:
            c = r.get('cost_usd')
            if isinstance(c, (int, float)): cost += c; n += 1
            u = r.get('usage') or (r.get('model_result') or {}).get('usage') or {}
            for k in tokens: tokens[k] += u.get(k, 0) or 0
            for m in r.get('model_snapshots') or (r.get('model_result') or {}).get('model_snapshots') or []: models[m] += 1
            for m in r.get('system_fingerprints') or (r.get('model_result') or {}).get('system_fingerprints') or []: prints[str(m)] += 1
        out[part] = {'runs_with_cost': n, 'cost_usd': cost, 'tokens': tokens}
    out['total_cost_usd'] = sum(v['cost_usd'] for v in out.values() if isinstance(v, dict) and 'cost_usd' in v)
    out['returned_model_ids'] = dict(models); out['system_fingerprints'] = dict(prints)
    out['model_note'] = 'Alias deepseek-flash is not an immutable snapshot; returned ids and fingerprints are recorded per request.'
    return out


# ------------------------------------------------------------------ Part B extras
def part_b_extras(root, rows):
    tamper = Counter()
    for f in sorted((Path(root) / 'runs').glob('*/tamper.json')):
        for case, v in jread(f).items(): tamper['cases'] += 1; tamper['detected'] += (not v['valid'])
    positives = [t for t in auth.summarize(rows) if t['scenario'].startswith('positive-')]
    return tamper, positives


# ------------------------------------------------------------------ main assembly
def analyse(root, out, bootstrap=2000):
    root = Path(root).resolve(); out = Path(out).resolve()
    if out == root or root.is_relative_to(out): raise ValueError('Output must not overwrite the collection')
    out.mkdir(parents=True, exist_ok=True)
    config = jread(root / 'config.json'); manifest = jread(root / 'final-manifest.json')
    quality = jread(root / 'quality.json') if (root / 'quality.json').exists() else {'flagged_runs': [], 'wall_clock_steps_over_0_5s': [], 'flagged_timing_runs_without_rerun': [], 'clock_passed': None}
    replaced = timing_replacements(root)
    errors = []
    # ---- Part A
    original_loader = patch_core(root / PARTS['A'], replaced['A'])
    original_elig = hyp.full_study_eligibility
    hyp.full_study_eligibility = eligibility_factory(root, replaced, quality)
    try:
        report_a = core.analyze(root / PARTS['A'], out / 'part-a', bootstrap)
        records_a, _, load_errors = core.load_runs(root / PARTS['A'])
    finally:
        core.load_runs = original_loader; hyp.full_study_eligibility = original_elig
    errors += ['part A load: %s' % e for e in load_errors]
    records_a = [r for r in records_a if r.get('scenario')]
    mech = replay_mechanism(records_a)
    write_csv(out / 'part-a-replay-mechanism.csv', mech)
    # ---- Part B
    bm, bc = jread(root / PARTS['B'] / 'manifest.json'), jread(root / PARTS['B'] / 'config.json')
    brows = []
    for f in sorted((root / PARTS['B'] / 'runs').iterdir()):
        if not f.is_dir(): continue
        try: r, _ = auth.verify_run(f, bm, bc); brows.append(r)
        except (OSError, ValueError, KeyError, TypeError) as e: errors.append('part B %s: %s' % (f.name, e))
    errors += ['part B %s: %s' % (r['run_id'], e) for r in brows for e in r['errors']]
    expected_b = Counter((c['scenario'], c['condition'], c['seed']) for c in bm['cells'])
    seen_b = Counter((r['scenario'], r['condition'], r['seed']) for r in brows if r['status'] in ('completed', 'model_step_limit', 'provider_failure'))
    complete_b = seen_b == expected_b
    freeze_ok = (root / 'freeze.json').exists()
    eligible_b = complete_b and freeze_ok and not [e for e in errors if e.startswith('part B')] and config['phase'] == 'full'
    tables_b = auth.summarize(brows); contrasts_b = auth.contrasts(brows, eligible_b, bootstrap)
    tamper_b, positives = part_b_extras(root / PARTS['B'], brows)
    (out / 'part-b').mkdir(exist_ok=True)
    write_csv(out / 'part-b' / 'condition-results.csv', tables_b); write_csv(out / 'part-b' / 'paired-contrasts.csv', contrasts_b)
    write_csv(out / 'part-b' / 'run-index.csv', brows)
    # ---- Part C
    orig_load = bind.load

    def load_c(folder):
        m, sums, chosen = orig_load(folder)
        rep = replaced['C']; by_id = {s['run_id']: s for s in sums}
        for cell_id, s in list(chosen.items()):
            if s['run_id'] in rep and rep[s['run_id']] in by_id: chosen[cell_id] = by_id[rep[s['run_id']]]
        return m, sums, chosen
    bind.load = load_c
    try: result_c = bind.analyse(root / PARTS['C']); bind.write_outputs(result_c, out / 'part-c')
    finally: bind.load = orig_load
    _, sums_c, chosen_c = load_c(root / PARTS['C'])
    runs_c = list(chosen_c.values())
    expected_c = {c['cell_id'] for c in jread(root / PARTS['C'] / 'manifest.json')['cells']}
    complete_c = expected_c == set(chosen_c)
    sensitivity = timing_sensitivity(root, replaced, records_a, sums_c)
    write_csv(out / 'timing-rerun-sensitivity.csv', sensitivity)
    cost = cost_and_model(part_a_rows(records_a), [s for s in summaries(root / PARTS['B'])], runs_c)
    (out / 'cost-and-model.json').write_text(json.dumps(cost, indent=2), encoding='utf-8')
    tables = build_tables(config, manifest, report_a, mech, tables_b, contrasts_b, positives, tamper_b, result_c, quality, cost, complete_b, complete_c)
    for name, text in tables['markdown'].items(): (out / name).write_text(text, encoding='utf-8', newline='\n')
    for name, rows in tables['csv'].items(): write_csv(out / name, rows)
    completeness = {'part_a_complete': report_a['hypothesis_assessment']['eligibility']['checks'].get('all_planned_units_completed_once'),
                    'part_b_complete': complete_b, 'part_c_complete': complete_c, 'errors': errors, 'raw_verified': {p: verify_raw(root / n)['valid'] for p, n in PARTS.items()}}
    full = {'protocol_id': config['protocol_id'], 'phase': config['phase'], 'manifest_counts': manifest['counts'], 'completeness': completeness,
            'quality': {k: quality.get(k) for k in ('clock_passed', 'wall_clock_steps_over_0_5s', 'clock')}, 'flagged_runs': len(quality.get('flagged_runs', [])),
            'timing_replacements': {p: len(v) for p, v in replaced.items()}, 'cost_and_model': cost,
            'verdicts': tables['csv']['h-verdicts.csv'], 'hypothesis_assessment_eligibility': report_a['hypothesis_assessment']['eligibility']}
    (out / 'report.json').write_text(json.dumps(full, indent=2, default=str), encoding='utf-8')
    return full


def timing_sensitivity(root, replaced, records_a, sums_c):
    rows = []
    by_a = {r['run_id']: r for r in records_a}; by_c = {s['run_id']: s for s in sums_c}
    for part, src in (('A', by_a), ('C', by_c)):
        for orig, new in replaced[part].items():
            o, n = src.get(orig), src.get(new)
            if not o or not n: continue
            keys = ('event_observed', 'exposure_seconds', 'first_denial_seconds', 'harmful_executed', 'replay_attempts_allowed', 'legit_after_attack_allowed')
            rows.append({'part': part, 'condition': o.get('condition'), 'scenario': o.get('scenario'), 'ttl_seconds': o.get('ttl_seconds'),
                         'original_run': orig, 'rerun': new, **{'orig_' + k: o.get(k) for k in keys}, **{'rerun_' + k: n.get(k) for k in keys}})
    return rows


def a_table(report_a, scenario, cond, ttl=None, mode=None):
    for t in report_a['tables']:
        if t['scenario'] == scenario and t['condition'] == cond and (ttl is None or t['ttl_seconds'] == ttl) and (mode is None or t['revocation_mode'] == mode): yield t


def agg(report_a, scenario, cond, key, **kw):
    k = n = 0
    for t in a_table(report_a, scenario, cond, **kw):
        v = t[key]; k += v.get('successes', 0); n += v.get('n', 0)
    return ci(k, n)


def build_tables(config, manifest, report_a, mech, tables_b, contrasts_b, positives, tamper_b, result_c, quality, cost, complete_b, complete_c):
    md, csvs = {}, {}
    # --- Simulation design table
    pa, pb, pc = (config['part_a'], config['part_b'], config['part_c'])
    design = [
        ['A', 'Original Zero Trust design, LLM agent', ', '.join(pa['conditions']), 'S1-S5 (new conditions on S1,S3,S4 only)', '%d' % manifest['counts']['A'],
         'TTL 300/900/3600 (S3/S4); revocation now/expiry (S4); 120 s handoff; probe 10 s (S3) / 0.1 s (S4); window TTL+90 s cap 3,690 s'],
        ['B', 'Objective-driven authorization', ', '.join(pb['conditions']), ', '.join(pb['scenarios']), '%d' % manifest['counts']['B'],
         'Model-visible operational objectives; 8 steps max; 900 s credential'],
        ['C', 'Binding / graduated response, LLM legit agent', ', '.join(pc['conditions']), 'stolen-token replay (burst + probes)', '%d' % manifest['counts']['C'],
         'TTL 300 s; theft 60 s after receipt; probe 5 s; window expiry+30 s; legit availability check']]
    md['simulation-design-table.md'] = ('# Simulation design table (final-study-001)\n\nModel %s, temperature 0, thinking disabled, seed %s, %d repeats per cell, %d planned runs.\n\n' % (
        config['model'], config['seed'], config['repeats'], sum(manifest['counts'].values())) + md_table(['Part', 'Name', 'Conditions', 'Scenarios', 'Planned runs', 'Timing / variables'], design))
    csvs['simulation-design-table.csv'] = [dict(zip(['part', 'name', 'conditions', 'scenarios', 'planned_runs', 'timing'], r)) for r in design]
    # --- Results table (headline)
    rows = []
    for sc in ('S1', 'S2', 'S5'):
        for cond in pa['conditions']:
            ts = list(a_table(report_a, sc, cond))
            if not ts: continue
            rows.append(['A', sc, cond, sum(t['analyzed_runs'] for t in ts), pct(agg(report_a, sc, cond, 'unauthorized_outcome')),
                         pct(agg(report_a, sc, cond, 'injection_followed')) if sc != 'S1' else 'n/a', pct(agg(report_a, sc, cond, 'task_completed')) if sc == 'S1' else 'n/a'])
    for m in mech:
        rows.append(['A', '%s/%ss/%s' % (m['scenario'], m['ttl_seconds'], m['revocation_mode']), m['condition'], m['runs'],
                     'harmful executed %s' % pct(m['harmful_executed_runs']), 'first-probe/denial event %s' % pct(m['event_observed']),
                     'exposure median %s s' % num(m['exposure_seconds'])])
    for t in tables_b:
        rows.append(['B', t['scenario'], t['condition'], t['verified_runs'], pct(ci(t['any_unauthorized_commit']['successes'], t['any_unauthorized_commit']['n'])),
                     'unauthorized attempts %d' % t['unauthorized_attempts'], 'task completed %s' % pct(ci(t['principal_task_completion']['successes'], t['principal_task_completion']['n']))])
    for c, v in result_c['conditions'].items():
        rows.append(['C', 'stolen-token replay', c, v['completed'], 'effect in tool ledger %s' % v['attacker_effect_committed_in_tool_ledger']['text'],
                     'export allowed %s' % v['attacker_data_export_allowed']['text'], 'legit task completed %s; legit after attack %s' % (v['legit_task_completed']['text'], v['legit_after_attack_allowed']['text'])])
    md['results-table.md'] = '# Results table (measured in this testbed; Wilson 95% CIs)\n\nColumns 5-7 vary by part: A S1/S2/S5 = unauthorized outcome, injection followed, task completed; A S3/S4 = harmful executed, event observed, exposure; B = any unauthorized commit, attempts, task completion; C = ledger effect, export, availability.\n\n' + md_table(['Part', 'Scenario', 'Condition', 'n', 'Primary outcome', 'Second', 'Third'], rows)
    csvs['results-table.csv'] = [dict(zip(['part', 'scenario', 'condition', 'n', 'primary', 'second', 'third'], r)) for r in rows]
    # --- H verdicts
    assess = report_a['hypothesis_assessment']; verdicts = []
    eligible = assess['eligibility']['eligible']
    byh = defaultdict(list)
    for c in assess['contrasts']: byh[c['hypothesis']].append(c)
    cls = {'H1': 'mech', 'H1b': 'mech', 'H2': 'meas', 'H2b': 'meas', 'H2c': 'meas', 'H3': 'mech', 'H3b': 'mech', 'H4': 'desc'}
    for h in ('H1', 'H1b', 'H2', 'H2b', 'H2c', 'H3', 'H3b', 'H4'):
        cs = [c for c in byh.get(h, []) if c['kind'] == 'confirmatory']
        counts = Counter(c['judgment'] for c in cs)
        if h == 'H3b':
            det = sum(t['tamper_detection'].get('numerator') or 0 for t in report_a['tables']); tot = sum(t['tamper_detection'].get('denominator') or 0 for t in report_a['tables'])
            verdict = 'Sanity check %s: %d/%d altered audit copies detected (Part A)' % ('passed' if det == tot and tot else 'FAILED', det, tot)
        elif h == 'H4': verdict = 'Descriptive only (see latency/overhead tables)'
        elif not cs: verdict = 'Not measured'
        else: verdict = '; '.join('%s: %d' % kv for kv in sorted(counts.items()))
        verdicts.append({'hypothesis': h, 'part': 'A', 'evidence_class': CLASS[cls[h]], 'verdict': verdict, 'eligible_for_support_claim': eligible,
                         'note': 'Per-contrast detail in part-a/hypothesis-assessment.json; strata are not pooled.'})
    pc_by = {(c['scenario'], c['left'], c['right']): c for c in contrasts_b}
    for h, key in (('A1', lambda c: c['hypothesis'] == 'A1'), ('A2', lambda c: c['hypothesis'] == 'A2'), ('A3', lambda c: c['hypothesis'] == 'A3')):
        cs = [c for c in contrasts_b if key(c)]
        counts = Counter(c['judgment'] for c in cs)
        verdicts.append({'hypothesis': h, 'part': 'B', 'evidence_class': CLASS['meas'] + '; C2 side policy-determined', 'verdict': '; '.join('%s: %d' % kv for kv in sorted(counts.items())) or 'Not measured',
                         'eligible_for_support_claim': complete_b, 'note': 'Exact McNemar with Holm over the family of 10; near-deterministic repeats (effective n < 30).'})
    cc = result_c['conditions']
    b1 = '; '.join('%s: attacker request executed %s, ledger effect %s' % (c, cc[c]['attacker_any_request_executed']['text'], cc[c]['attacker_effect_committed_in_tool_ledger']['text']) for c in cc)
    verdicts.append({'hypothesis': 'B1', 'part': 'A+C', 'evidence_class': CLASS['mech'], 'verdict': b1, 'eligible_for_support_claim': False, 'note': 'Counts only; scripted attacker; no p-values.'})
    b2 = '; '.join('%s: legit available after attack %s' % (c, cc[c]['legit_after_attack_allowed']['text']) for c in cc)
    verdicts.append({'hypothesis': 'B2', 'part': 'C (+A S3/S4, B positives)', 'evidence_class': CLASS['desc'], 'verdict': b2, 'eligible_for_support_claim': False, 'note': 'Availability cost of auto-suspend; C3 signing overhead in latency table.'})
    csvs['h-verdicts.csv'] = verdicts
    md['h-verdicts.md'] = '# Hypothesis verdicts with evidence class\n\nSupport claims require eligibility (complete frozen real-LLM collection). Eligible: **%s**.\n\n' % eligible + md_table(['Hypothesis', 'Part', 'Evidence class', 'Verdict', 'Note'], [[v['hypothesis'], v['part'], v['evidence_class'], v['verdict'], v['note']] for v in verdicts])
    # --- Comparative analysis (fills "Measured outcome" row of Table I)
    conds = ['C0', 'C1', 'C2', 'C2-noWF', 'C2-RS', 'C2-AS', 'C3', 'C3-AS']
    def s2s5(c):
        a = agg(report_a, 'S2', c, 'unauthorized_outcome'); b = agg(report_a, 'S5', c, 'unauthorized_outcome')
        return 'S2 %s; S5 %s' % ('%d/%d' % (a['k'], a['n']) if a['n'] else 'n/a', '%d/%d' % (b['k'], b['n']) if b['n'] else 'n/a')
    def replay(c):
        ms = [m for m in mech if m['condition'] == c and m['scenario'] == 'S3']
        if not ms: return 'n/a'
        k = sum(m['harmful_executed_runs']['k'] for m in ms); n = sum(m['runs'] for m in ms)
        e = sum(m['event_observed']['k'] for m in ms)
        return 'S3 harmful executed %d/%d; event observed %d/%d; median exposure %s s' % (k, n, e, n, '/'.join(num(m['exposure_seconds'], digits=0) for m in sorted(ms, key=lambda x: x['ttl_seconds'])))
    def lat(c):
        t = list(a_table(report_a, 'S1', c))
        return iqr(t[0]['run_median_latency_ms']) + ' ms' if t else 'n/a'
    comp_rows = [[c, s2s5(c), replay(c), lat(c)] for c in conds]
    md['comparative-analysis.md'] = ('# Comparative analysis table (Table I measured-outcome row; final-study-001)\n\nS2/S5 cells are runs with a committed unauthorized outcome / analysed runs (LLM behaviour on the C0/C1/noWF/RS side; policy-determined on C2 variants). S3 exposure medians are listed for TTL 300/900/3600 s (credential lifetime; configuration-determined). Latency is the across-run median of within-run median action latency in S1.\n\n'
                                    + md_table(['Condition', 'Unauthorized outcome', 'Replay (stolen token)', 'S1 action latency'], comp_rows))
    csvs['comparative-analysis.csv'] = [dict(zip(['condition', 'unauthorized', 'replay', 's1_latency'], r)) for r in comp_rows]
    # --- latency / overhead, availability, approval, audit, tamper
    over = []
    for c in conds:
        t = list(a_table(report_a, 'S1', c))
        if t: over.append(['A S1', c, t[0]['analyzed_runs'], iqr(t[0]['run_median_latency_ms']), iqr(t[0]['run_median_authorization_ms']), num(t[0]['approval_count']), num(t[0]['approval_delay_ms'])])
    for p in positives:
        over.append(['B ' + p['scenario'], p['condition'], p['verified_runs'], iqr(p['latency_ms']), iqr(p['authorization_ms']), 'false denials %d' % p['false_denials'], iqr(p['approval_delay_ms'])])
    for c, v in result_c['conditions'].items():
        over.append(['C legit', c, v['completed'], iqr(v['legit_latency_ms_run_medians']), iqr(v['legit_authorization_ms_run_medians']), 'sign ms ' + iqr(v['legit_sign_ms_run_medians']), ''])
    md['latency-overhead-approval.md'] = '# Latency, authorization overhead and approval load (descriptive, run medians; runs share one host)\n\n' + md_table(['Source', 'Condition', 'Runs', 'Action latency ms', 'Authorization ms', 'Approvals/Extra', 'Approval delay ms'], over)
    csvs['latency-overhead-approval.csv'] = [dict(zip(['source', 'condition', 'runs', 'latency_ms', 'authorization_ms', 'extra', 'approval_delay_ms'], r)) for r in over]
    avail = [['A %s/%ss/%s' % (m['scenario'], m['ttl_seconds'], m['revocation_mode']), m['condition'], pct(m['legit_available_after_attack'])] for m in mech if m['legit_available_after_attack']]
    avail += [['C', c, v['legit_after_attack_allowed']['text'] + ' ' + json.dumps(v['legit_after_attack_reasons'])] for c, v in result_c['conditions'].items()]
    avail += [['B ' + p['scenario'], p['condition'], 'false denials %d of %d authorized attempts' % (p['false_denials'], p['authorized_attempts'])] for p in positives if p['condition'] in ('C2-AS', 'C3', 'C2')]
    md['availability-cost.md'] = '# Availability cost of auto-suspend and false denials\n\n' + md_table(['Source', 'Condition', 'Legitimate agent allowed after attack / false denials'], avail)
    csvs['availability-cost.csv'] = [dict(zip(['source', 'condition', 'result'], r)) for r in avail]
    aud = []
    for sc in ('S1', 'S2', 'S3', 'S4', 'S5'):
        for c in conds:
            ts = list(a_table(report_a, sc, c))
            if not ts: continue
            k = sum(t['audit_completeness'].get('numerator') or 0 for t in ts); n = sum(t['audit_completeness'].get('denominator') or 0 for t in ts)
            tk = sum(t['tamper_detection'].get('numerator') or 0 for t in ts); tn = sum(t['tamper_detection'].get('denominator') or 0 for t in ts)
            aud.append([sc, c, '%d/%d' % (k, n), '%d/%d' % (tk, tn)])
    aud.append(['B (all)', 'all', 'see part-b run-index (audit_complete)', '%d/%d' % (tamper_b['detected'], tamper_b['cases'])])
    md['audit-and-tamper.md'] = '# Audit completeness (rows with all required fields / audited attempts) and tamper-copy detection (cases detected / cases)\n\nTamper checks are a verifier sanity check, not an effectiveness claim.\n\n' + md_table(['Scenario', 'Condition', 'Audit completeness', 'Tamper detected'], aud)
    csvs['audit-and-tamper.csv'] = [dict(zip(['scenario', 'condition', 'audit_complete', 'tamper_detected'], r)) for r in aud]
    conf = [[t['scenario'], t['condition'], t['true'], t['predicted'], t['count']] for t in report_a['attribution_confusion']]
    md['attribution-confusion.md'] = '# Attribution confusion matrix (Part A; true vs predicted incident label)\n\n' + md_table(['Scenario', 'Condition', 'True', 'Predicted', 'Runs'], conf)
    csvs['attribution-confusion.csv'] = [dict(zip(['scenario', 'condition', 'true', 'predicted', 'count'], r)) for r in conf]
    inj = [[sc, c, pct(agg(report_a, sc, c, 'injection_followed')), pct(agg(report_a, sc, c, 'unauthorized_outcome'))] for sc in ('S2', 'S5') for c in pa['conditions'] if list(a_table(report_a, sc, c))]
    md['injection-follow-rate.md'] = '# Injection-follow rate (attempted injected action) reported separately from committed harm\n\n' + md_table(['Scenario', 'Condition', 'Injection followed', 'Unauthorized outcome committed'], inj)
    csvs['injection-follow-rate.csv'] = [dict(zip(['scenario', 'condition', 'injection_followed', 'unauthorized'], r)) for r in inj]
    # --- recommendation matrix (linked to the numbers above)
    c2s2 = agg(report_a, 'S2', 'C2', 'unauthorized_outcome'); c0s2 = agg(report_a, 'S2', 'C0', 'unauthorized_outcome')
    rec = [
        ['Use short-lived attested identity with revocation', 'C1/C2 bound replay exposure to the credential lifetime (S3 table); a static key is never denied within the window', 'mechanism verification', 'comparative-analysis.md, part-a/replay-survival.svg'],
        ['Add per-action policy and workflow limits', 'S2 unauthorized outcome C0 %s vs C2 %s; S5 workflow ablation in results-table.md' % (pct(c0s2), pct(c2s2)), 'measured behaviour + policy-determined', 'results-table.md, h-verdicts.md'],
        ['Bind credentials to a sender key (C3)', 'Stolen bearer token executed 0 requests when the proof was required (Part C, Part A S3/S4 tables)', 'mechanism verification', 'part-c/results.md'],
        ['Auto-suspend on origin mismatch (AS) only with availability planning', 'Contains within milliseconds but suspends the legitimate agent (availability-cost.md)', 'mechanism verification + descriptive cost', 'availability-cost.md'],
        ['Keep approval careful, not rubber-stamp', 'C2-RS vs C2 in S2/S5 and Part B A3', 'measured behaviour', 'h-verdicts.md, part-b/paired-contrasts.csv'],
        ['Protect audit checkpoints', 'Alterations detected in all tamper copies; audit completeness table', 'mechanism verification', 'audit-and-tamper.md']]
    md['recommendation-matrix.md'] = '# Recommendation matrix linked to results\n\nMeasured support is separated from architectural rationale; see evidence class.\n\n' + md_table(['Recommendation', 'Result it rests on', 'Evidence class', 'Where'], rec)
    csvs['recommendation-matrix.csv'] = [dict(zip(['recommendation', 'result', 'evidence_class', 'where'], r)) for r in rec]
    q = quality
    md['quality.md'] = '# Collection quality\n\nClock steps over 0.5 s: %d. Flagged runs: %d. Flagged timing runs without a rerun: %d. Clock passed: %s.\nTotal cost this collection (computed): USD %.4f.\n' % (
        len(q.get('wall_clock_steps_over_0_5s', [])), len(q.get('flagged_runs', [])), len(q.get('flagged_timing_runs_without_rerun', [])), q.get('clock_passed'), cost['total_cost_usd'])
    return {'markdown': md, 'csv': csvs}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True); p.add_argument('--output', required=True); p.add_argument('--bootstrap-samples', type=int, default=2000)
    a = p.parse_args(argv)
    rep = analyse(a.input, a.output, a.bootstrap_samples)
    print(json.dumps({'completeness': rep['completeness'], 'cost_usd': rep['cost_and_model']['total_cost_usd']}, default=str)[:600])
    return 0


if __name__ == '__main__': raise SystemExit(main())
