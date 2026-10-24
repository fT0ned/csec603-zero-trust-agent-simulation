"""Offline, deterministic analysis of a binding-response-study collection (stdlib only).

Usage: python -m analysis.binding_study --input results/binding-study-001 --output results/binding-study-001/analysis
All security contrasts are mechanism verification (configuration-determined, scripted attacker); no hypothesis tests.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

ORDER = ['C1', 'C2', 'C2-AS', 'C3', 'C3-AS']
NAMES = {'C1': 'C1 short-lived ID (bearer)', 'C2': 'C2 full Zero Trust (log only)', 'C2-AS': 'C2-AS auto-suspend',
         'C3': 'C3 key-bound credential', 'C3-AS': 'C3-AS key-bound + auto-suspend'}
FRAME = 'Mechanism verification (configuration-determined, scripted attacker); not a hypothesis test. Repeats are near-deterministic.'


def wilson(k, n, z=1.96):
    if n == 0: return (None, None)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - h) / d), min(1.0, (c + h) / d))


def frac(k, n):
    lo, hi = wilson(k, n)
    return {'k': k, 'n': n, 'text': '%d/%d' % (k, n), 'wilson95': None if lo is None else [round(lo, 4), round(hi, 4)]}


def quantile(values, q):
    if not values: return None
    v = sorted(values); pos = (len(v) - 1) * q; lo = math.floor(pos); hi = math.ceil(pos)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def describe(values):
    if not values: return {'n': 0, 'median': None, 'q1': None, 'q3': None, 'min': None, 'max': None}
    return {'n': len(values), 'median': statistics.median(values), 'q1': quantile(values, .25), 'q3': quantile(values, .75), 'min': min(values), 'max': max(values)}


def kaplan_meier(times):
    """times: list of (time, event_bool). Returns table rows and a quantile function; censored values are never averaged."""
    rows = []; at_risk = len(times); surv = 1.0
    for t in sorted({t for t, _ in times}):
        d = sum(1 for x, e in times if x == t and e); c = sum(1 for x, e in times if x == t and not e)
        if d: surv *= 1 - d / at_risk
        rows.append({'time': round(t, 3), 'at_risk': at_risk, 'events': d, 'censored': c, 'survival': round(surv, 6)})
        at_risk -= d + c
    return rows


def km_quantile(rows, q, last):
    """Smallest time at which survival <= 1-q, or the string '> last-observed' when not reached (right-censored)."""
    for r in rows:
        if r['survival'] <= 1 - q + 1e-12: return r['time']
    return '> %.0f s (censored; window end)' % last


def load(folder):
    folder = Path(folder); manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    summaries = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((folder / 'runs').glob('*/summary.json'))]
    chosen = {}
    for s in sorted(summaries, key=lambda s: (s['cell_id'], 'rerun_of' in s, s['run_id'])):
        if s['status'] == 'completed' and s['cell_id'] not in chosen: chosen[s['cell_id']] = s
    return manifest, summaries, chosen


def counts(values):
    out = {}
    for v in values: out[str(v)] = out.get(str(v), 0) + 1
    return dict(sorted(out.items()))


def analyse(folder):
    manifest, summaries, chosen = load(folder)
    conditions = [c for c in ORDER if any(s['condition'] == c for s in chosen.values()) or any(x['condition'] == c for x in manifest['cells'])]
    result = {'frame': FRAME, 'phase': manifest['phase'], 'git_commit': manifest['git_commit'], 'planned_runs': manifest['count'],
              'completed_runs': len(chosen), 'excluded_or_failed_attempts': sum(1 for s in summaries if s['status'] != 'completed'), 'conditions': {}}
    for c in conditions:
        runs = [s for s in chosen.values() if s['condition'] == c]; n = len(runs)
        planned = sum(1 for x in manifest['cells'] if x['condition'] == c)
        survival = [((r['first_denial_seconds'], True) if r['event_observed'] else (r['censored_at_seconds'], False)) for r in runs]
        km = kaplan_meier(survival); last = max((t for t, _ in survival), default=0)
        window = runs[0]['window_seconds'] if runs else 0
        contain = [r['detection_to_containment_ms'] for r in runs if r.get('detection_to_containment_ms') is not None]
        c2 = c != 'C1'
        def cnt(key): return frac(sum(bool(r[key]) for r in runs), n)
        result['conditions'][c] = {
            'name': NAMES[c], 'planned': planned, 'completed': n,
            'attacker_any_request_executed': cnt('first_attacker_success'),
            'attacker_data_export_allowed': cnt('burst_export_allowed'), 'attacker_email_to_attacker_allowed': cnt('burst_email_allowed'),
            'attacker_effect_committed_in_tool_ledger': frac(sum(r['attacker_committed_writes'] > 0 for r in runs), n),
            'attacker_records_exported_total': sum(r['attacker_committed_records'] for r in runs),
            'replay_attempts_allowed': describe([r['replay_attempts_allowed'] for r in runs]),
            'attacker_events_denied_by_end': cnt('event_observed'),
            'time_to_first_probe_denial_km': {'rows': km, 'q25': km_quantile(km, .25, last), 'median': km_quantile(km, .5, last), 'q75': km_quantile(km, .75, last),
                                              'censored_runs': sum(not e for _, e in survival), 'window_seconds_median': window},
            'last_successful_attacker_request_seconds': dict(describe([r['exposure_seconds'] for r in runs]), note='for censored runs this is a lower bound'),
            'first_probe_denial_reasons': counts(r['first_denial_reason'] for r in runs),
            'first_burst_denial_reasons': counts(r['first_burst_reason'] for r in runs),
            'detection_to_containment_ms': describe(contain) if c.endswith('AS') else None,
            'containment_recorded': frac(len(contain), n) if c.endswith('AS') else None,
            'legit_task_completed': cnt('legit_task_completed'), 'legit_after_attack_allowed': cnt('legit_after_attack_allowed'),
            'legit_after_attack_reasons': counts(r['legit_after_attack_reason'] for r in runs),
            'audit_chain_valid': cnt('audit_valid'),
            'audit_flags_impersonation': frac(sum(bool(r['audit_flags_impersonation']) for r in runs), n) if c2 else None,
            'audit_c2_fields_complete_rows': '%d/%d' % (sum(r['audit_c2_fields_complete'] for r in runs), sum(r['audit_count'] for r in runs)) if c2 else None,
            'tamper_cases_detected': '%d/%d' % (sum(r['tamper_detected'] for r in runs), sum(r['tamper_cases'] for r in runs)),
            'legit_latency_ms_run_medians': describe([r['legit_latency_ms_median'] for r in runs if r['legit_latency_ms_median'] is not None]),
            'legit_sign_ms_run_medians': describe([r['legit_sign_ms_median'] for r in runs if r.get('legit_sign_ms_median') is not None]),
            'legit_authorization_ms_run_medians': describe([r['legit_authorization_ms_median'] for r in runs if r.get('legit_authorization_ms_median') is not None]),
        }
    lat = {c: v['legit_latency_ms_run_medians']['median'] for c, v in result['conditions'].items()}
    result['c3_vs_c2_latency'] = {'note': 'Descriptive medians of per-run medians; legit requests only; concurrent runs share the host. Excludes client-side signing, reported separately.',
        'pairs': {a + ' minus ' + b: (None if lat.get(a) is None or lat.get(b) is None else round(lat[a] - lat[b], 3)) for a, b in (('C3', 'C2'), ('C3-AS', 'C2-AS'))}}
    return result


def svg_bars(path, title, items, unit, maximum=None):
    top = maximum or max([v for _, v, _ in items] + [1]); w = 640; h = 60 + 46 * len(items)
    rows = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="sans-serif" font-size="14"><rect width="100%%" height="100%%" fill="#fff"/>' % (w, h),
            '<text x="10" y="24" font-size="16" font-weight="bold">%s</text>' % title]
    for i, (label, value, color) in enumerate(items):
        y = 44 + 46 * i; bar = 360 * value / top if top else 0
        rows.append('<text x="10" y="%d">%s</text><rect x="230" y="%d" width="%.1f" height="22" fill="%s"/><text x="%.1f" y="%d">%s</text>'
                    % (y + 16, label, y, bar, color, 236 + bar, y + 16, ('%g' % round(value, 2)) + unit))
    open(path, 'w', encoding='utf-8', newline='\n').write(''.join(rows) + '</svg>\n')


def svg_km(path, result):
    w, h, left, bottom = 640, 360, 60, 310; xmax = max([r['time'] for c in result['conditions'].values() for r in c['time_to_first_probe_denial_km']['rows']] + [1])
    colors = {'C1': '#d55e00', 'C2': '#e69f00', 'C2-AS': '#0072b2', 'C3': '#009e73', 'C3-AS': '#cc79a7'}
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="sans-serif" font-size="13"><rect width="100%%" height="100%%" fill="#fff"/>' % (w, h),
           '<text x="10" y="22" font-size="16" font-weight="bold">Stolen token still working (fraction of runs) vs seconds after theft</text>',
           '<line x1="%d" y1="40" x2="%d" y2="%d" stroke="#000"/><line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#000"/>' % (left, left, bottom, left, bottom, w - 20, bottom),
           '<text x="%d" y="%d">0</text><text x="%d" y="%d">1.0</text><text x="%d" y="%d">%d s</text>' % (30, bottom, 30, 48, w - 70, bottom + 18, xmax)]
    for i, (c, v) in enumerate(result['conditions'].items()):
        pts = ['%d,%d' % (left, 48)]; prev = 1.0
        for r in v['time_to_first_probe_denial_km']['rows']:
            x = left + (w - 80 - left) * r['time'] / xmax
            pts.append('%.1f,%.1f' % (x, 48 + (bottom - 48) * (1 - prev))); pts.append('%.1f,%.1f' % (x, 48 + (bottom - 48) * (1 - r['survival']))); prev = r['survival']
        pts.append('%d,%.1f' % (w - 80, 48 + (bottom - 48) * (1 - prev)))
        out.append('<polyline fill="none" stroke="%s" stroke-width="3" points="%s"/><text x="%d" y="%d" fill="%s">%s</text>' % (colors[c], ' '.join(pts), 70 + 110 * i, bottom + 40, colors[c], c))
    open(path, 'w', encoding='utf-8', newline='\n').write(''.join(out) + '</svg>\n')


def write_outputs(result, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True); C = result['conditions']
    (out / 'results.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    with (out / 'summary-table.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['condition', 'n', 'any_attacker_request_executed', 'export_allowed', 'attacker_email_allowed', 'committed_attacker_effect', 'attacker_records_exported',
                    'median_probe_denial_s', 'censored_runs', 'containment_ms_median', 'legit_after_attack_allowed', 'legit_task_completed', 'audit_flags_impersonation'])
        for c, v in C.items():
            w.writerow([c, v['completed'], v['attacker_any_request_executed']['text'], v['attacker_data_export_allowed']['text'], v['attacker_email_to_attacker_allowed']['text'],
                        v['attacker_effect_committed_in_tool_ledger']['text'], v['attacker_records_exported_total'], v['time_to_first_probe_denial_km']['median'],
                        v['time_to_first_probe_denial_km']['censored_runs'], (v['detection_to_containment_ms'] or {}).get('median'), v['legit_after_attack_allowed']['text'],
                        v['legit_task_completed']['text'], (v['audit_flags_impersonation'] or {}).get('text')])
    with (out / 'survival-km.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['condition', 'time_seconds', 'n_at_risk', 'events', 'censored', 'survival'])
        for c, v in C.items():
            for r in v['time_to_first_probe_denial_km']['rows']: w.writerow([c, r['time'], r['at_risk'], r['events'], r['censored'], r['survival']])
    with (out / 'detection-to-containment.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['condition', 'n', 'median_ms', 'q1_ms', 'q3_ms', 'min_ms', 'max_ms'])
        for c, v in C.items():
            d = v['detection_to_containment_ms']
            if d: w.writerow([c, d['n'], d['median'], d['q1'], d['q3'], d['min'], d['max']])
    pal = {'C1': '#d55e00', 'C2': '#e69f00', 'C2-AS': '#0072b2', 'C3': '#009e73', 'C3-AS': '#cc79a7'}
    svg_bars(out / 'fig-attacker-success.svg', 'Runs where the stolen token worked at least once (%)',
             [(c, round(100 * v['attacker_any_request_executed']['k'] / max(1, v['completed']), 1), pal[c]) for c, v in C.items()], '%', 100)
    svg_bars(out / 'fig-availability-cost.svg', 'Runs where the legitimate agent was locked out right after the attack (%)',
             [(c, round(100 * (v['legit_after_attack_allowed']['n'] - v['legit_after_attack_allowed']['k']) / max(1, v['completed']), 1), pal[c]) for c, v in C.items()], '%', 100)
    svg_km(out / 'fig-exposure-survival.svg', result)
    lines = ['# Binding-response study: results', '', '**' + FRAME + '**', '',
             'Collection: %s phase, git commit %s. %d of %d planned runs completed (%d failed or excluded attempts retained in raw data).' % (
                 result['phase'], result['git_commit'][:10], result['completed_runs'], result['planned_runs'], result['excluded_or_failed_attempts']), '',
             '## What happened, in plain English', '']
    for c, v in C.items():
        km = v['time_to_first_probe_denial_km']
        s = '- **%s** (%d runs): the stolen token executed at least one attacker request in %s runs (data export allowed %s, email to the attacker allowed %s); ' % (
            v['name'], v['completed'], v['attacker_any_request_executed']['text'], v['attacker_data_export_allowed']['text'], v['attacker_email_to_attacker_allowed']['text'])
        s += 'a committed attacker effect appears in the independent tool ledger in %s runs (%d records exported by the attacker). ' % (v['attacker_effect_committed_in_tool_ledger']['text'], v['attacker_records_exported_total'])
        if km['censored_runs']: s += 'Median time until the probe was first refused: %s (%d runs never refused within the window). ' % (km['median'], km['censored_runs'])
        else: s += 'Median seconds after theft until the probe was first refused: %s. ' % km['median']
        if v['detection_to_containment_ms']: s += 'Detection to containment: median %.1f ms (n=%d). ' % (v['detection_to_containment_ms']['median'], v['detection_to_containment_ms']['n'])
        s += 'The legitimate agent could still work right after the attack in %s runs (reasons: %s).' % (v['legit_after_attack_allowed']['text'], json.dumps(v['legit_after_attack_reasons']))
        lines.append(s)
    lines += ['', '## Table: stolen-token outcomes (counts with Wilson 95% intervals)', '',
              '| Condition | Any attacker request executed | Data export allowed | Email to attacker allowed | Effect in tool ledger |', '|---|---|---|---|---|']
    for c, v in C.items():
        cell = lambda k: '%s [%.2f, %.2f]' % (v[k]['text'], *v[k]['wilson95'])
        lines.append('| %s | %s | %s | %s | %s |' % (c, cell('attacker_any_request_executed'), cell('attacker_data_export_allowed'), cell('attacker_email_to_attacker_allowed'), cell('attacker_effect_committed_in_tool_ledger')))
    lines += ['', '## Table: exposure (seconds after theft until the harmless probe is first refused)', '',
              'Kaplan-Meier handling: runs where the probe was never refused before the window ended are right-censored and never averaged; quantiles not reached are reported as "> window".', '',
              '| Condition | Q25 | Median | Q75 | Censored runs | Last successful attacker request, median (lower bound if censored) |', '|---|---|---|---|---|---|']
    for c, v in C.items():
        km = v['time_to_first_probe_denial_km']; last = v['last_successful_attacker_request_seconds']
        lines.append('| %s | %s | %s | %s | %d | %s |' % (c, km['q25'], km['median'], km['q75'], km['censored_runs'], None if last['median'] is None else round(last['median'], 2)))
    lines += ['', '## Table: detection to containment (AS conditions)', '', '| Condition | n | Median ms | IQR ms | Min | Max |', '|---|---|---|---|---|---|']
    for c, v in C.items():
        d = v['detection_to_containment_ms']
        if d and d['n']: lines.append('| %s | %d | %.2f | %.2f to %.2f | %.2f | %.2f |' % (c, d['n'], d['median'], d['q1'], d['q3'], d['min'], d['max']))
    lines += ['', '## Table: availability cost (legitimate agent right after the attack burst)', '', '| Condition | Legitimate task completed before theft | Legitimate request allowed after attack | Reasons when denied |', '|---|---|---|---|']
    for c, v in C.items(): lines.append('| %s | %s | %s | %s |' % (c, v['legit_task_completed']['text'], v['legit_after_attack_allowed']['text'], json.dumps(v['legit_after_attack_reasons'])))
    lines += ['', '## Table: audit evidence', '', '| Condition | Audit chain valid | Audit flags impersonation | Full C2 fields in rows | Tamper cases detected |', '|---|---|---|---|---|']
    for c, v in C.items(): lines.append('| %s | %s | %s | %s | %s |' % (c, v['audit_chain_valid']['text'], (v['audit_flags_impersonation'] or {}).get('text', 'n/a'), v['audit_c2_fields_complete_rows'] or 'n/a', v['tamper_cases_detected']))
    lines += ['', '## Table: latency of legitimate requests (descriptive; median of per-run medians, milliseconds)', '',
              '| Condition | Gateway round trip | Client signing | PA authorization |', '|---|---|---|---|']
    f = lambda d: 'n/a' if d['median'] is None else '%.2f (IQR %.2f to %.2f)' % (d['median'], d['q1'], d['q3'])
    for c, v in C.items(): lines.append('| %s | %s | %s | %s |' % (c, f(v['legit_latency_ms_run_medians']), f(v['legit_sign_ms_run_medians']), f(v['legit_authorization_ms_run_medians'])))
    lines += ['', 'Difference of medians (round trip only, runs executed concurrently on one host): %s.' % json.dumps(result['c3_vs_c2_latency']['pairs']), '',
              '## Figures', '', '- fig-attacker-success.svg', '- fig-exposure-survival.svg', '- fig-availability-cost.svg', '',
              'Machine-readable: results.json, summary-table.csv, survival-km.csv, detection-to-containment.csv.', '']
    (out / 'results.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(); write_outputs(analyse(args.input), args.output)


if __name__ == '__main__': main()
