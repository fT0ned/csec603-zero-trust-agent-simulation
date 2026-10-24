"""Final consolidated real-LLM collection (final-study-001): one protocol, one freeze, one manifest.

Part A  original Zero Trust design (S1-S5) plus C2-AS / C3 / C3-AS on S1, S3, S4   -> testbed.runner.run_one
Part B  objective-driven authorization (24 original cells + C2-AS/C3 positive controls) -> testbed.authorization_study.run_one
Part C  binding / graduated response with the real LLM as the legitimate agent      -> testbed.binding_study.run_one

Existing per-run functions are called unchanged; this module only plans cells, schedules them on worker pools,
retries infrastructure failures once (linked, originals kept), and judges host clock quality from timestamps alone.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import copy
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import authorization_study as part_b
from . import binding_study as part_c
from . import runner as part_a
from .common import ROOT, canonical, digest, write_json
from .power import keep_awake

PARTS = {'A': 'part-a', 'B': 'part-b', 'C': 'part-c'}
TAG = 'final-study-freeze-v1'
FREEZE_PATH = ROOT / 'configs' / 'final-study-freeze.json'
FREEZE_FILES = ['testbed/final_study.py', 'testbed/runner.py', 'testbed/authorization_study.py', 'testbed/binding_study.py',
                'testbed/agent.py', 'testbed/service.py', 'testbed/client.py', 'testbed/probe.py', 'testbed/binding.py', 'testbed/fixtures.py',
                'testbed/prompts.py', 'testbed/audit.py', 'infra/opa/policy.rego', 'infra/tools.py',
                'analysis/final_study.py', 'analysis/run.py', 'analysis/hypotheses.py', 'analysis/authorization_study.py', 'analysis/binding_study.py',
                'analysis/statistics.py', 'scripts/collect_final_study.py', 'docs/final-study-protocol.md', 'docs/analysis-plan.md']
INFRA = {'A': {'infrastructure_failure', 'running'}, 'B': {'infrastructure_failure', 'evidence_failure', 'running'},
         'C': {'infrastructure_failure', 'evidence_failure', 'running'}}
STEP_SECONDS = 0.5


def lf_hash(name): return hashlib.sha256((ROOT / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


# ---------------------------------------------------------------- configuration
def part_config(config, part):
    """Derived per-part config in the shape the existing run functions expect."""
    common = {k: config[k] for k in ('protocol_id', 'study_kind', 'phase', 'mode', 'model', 'seed', 'repeats', 'budget_usd', 'final_study') if k in config}
    common['monotonic_timing'] = bool(config.get('monotonic_timing'))
    spec = copy.deepcopy(config['part_' + part.lower()])
    out = {**common, **spec}
    out['study_kind'] = {'A': 'original-zero-trust-llm', 'B': 'objective-driven-authorization', 'C': 'binding-response'}[part]
    out['protocol_id'] = config['protocol_id'] + '/part-' + part.lower()
    if part == 'B': out.setdefault('max_steps', 8)
    return out


def validate_config(config):
    if config.get('final_study') is not True or config.get('mode') != 'llm': raise ValueError('Final study requires final_study=true and mode=llm')
    if config.get('phase') not in ('pilot', 'full'): raise ValueError('phase must be pilot or full')
    if config.get('model') != 'deepseek-flash': raise ValueError('The final study uses deepseek-flash only (no fallback)')
    if not config.get('monotonic_timing'): raise ValueError('monotonic_timing must be enabled')
    stages = config.get('stages', [['B', 'C'], ['A']])
    if sorted(p for s in stages for p in s) != ['A', 'B', 'C']: raise ValueError('stages must cover parts A, B, C exactly once')
    if config['phase'] == 'full':
        if config.get('repeats') != 30: raise ValueError('Full collection uses 30 repeats')
        validate_freeze(config)


def validate_freeze(config):
    freeze = json.loads(FREEZE_PATH.read_text(encoding='utf-8'))
    if freeze.get('status') != 'frozen' or freeze.get('tag') != TAG: raise ValueError('Final-study freeze is not frozen')
    if digest(config) != freeze.get('config_sha256'): raise ValueError('Configuration differs from the frozen final study')
    for name, expected in freeze['file_hashes'].items():
        if lf_hash(name) != expected: raise ValueError('Frozen source changed: ' + name)
    tagged = subprocess.run(['git', 'show', TAG + ':configs/final-study-freeze.json'], cwd=ROOT, text=True, capture_output=True)
    if tagged.returncode or json.loads(tagged.stdout) != freeze: raise ValueError('Commit and tag the exact freeze before collection')
    local = subprocess.check_output(['git', 'rev-parse', TAG], cwd=ROOT, text=True).strip()
    remote = subprocess.check_output(['git', 'ls-remote', 'origin', 'refs/tags/' + TAG], cwd=ROOT, text=True).split()
    if not remote or remote[0] != local: raise ValueError('Push the freeze tag before full collection')
    return freeze


def make_freeze(config_path, pilot_reference):
    config = json.loads(Path(config_path).read_text(encoding='utf-8'))
    return {'status': 'frozen', 'tag': TAG, 'protocol_id': config['protocol_id'], 'config_file': Path(config_path).as_posix(),
            'config_sha256': digest(config), 'hash_scheme': 'sha256 of LF-normalized bytes',
            'file_hashes': {n: lf_hash(n) for n in FREEZE_FILES}, 'analysis_plan_sha256': lf_hash('docs/analysis-plan.md'),
            'pilot_reference': pilot_reference, 'timing_rerun_rule': (
                'Part A S3/S4 and Part C runs overlapping a detected host wall-clock step >0.5 s (or with |handoff error| >1 s) receive exactly one '
                'linked same-cell rerun, decided by timestamps only; originals are preserved and reported in a sensitivity table.')}


# ---------------------------------------------------------------- cells
def uid(part, row):
    if part == 'A': return canonical([row['condition'], row['scenario'], row['ttl_seconds'], row['revocation_mode'], row['seed']])
    if part == 'B': return canonical([row['condition'], row['scenario'], row['seed']])
    return row['cell_id']


RUNNERS = {'A': part_a.run_one, 'B': part_b.run_one, 'C': part_c.run_one}
PREPARE = {'A': part_a.prepare_batch, 'B': part_b.prepare_batch, 'C': part_c.prepare_batch}


def expected_counts(config):
    """Planned cells per part without touching the filesystem (used by tests/protocol)."""
    out = {}
    out['A'] = part_a.manifest(part_config(config, 'A'))
    out['B'] = part_b.manifest(part_config(config, 'B'))
    out['C'] = part_c.manifest(part_config(config, 'C'))
    return out


def read_summaries(directory):
    rows = []
    for p in sorted((Path(directory) / 'runs').glob('*/summary.json')):
        try: rows.append(json.loads(p.read_text(encoding='utf-8')))
        except (OSError, ValueError): pass
    return rows


# ---------------------------------------------------------------- clock evidence
class ClockMonitor:
    """Sample wall vs monotonic clock every second (host)."""

    def __init__(self): self.samples = []; self._stop = threading.Event(); self._thread = None

    def __enter__(self):
        def loop():
            while True:
                a = time.monotonic(); wall = time.time(); b = time.monotonic()
                self.samples.append({'wall_time': wall, 'monotonic_low': a, 'monotonic_high': b})
                if self._stop.wait(1): return
        self._thread = threading.Thread(target=loop, daemon=True); self._thread.start(); return self

    def __exit__(self, *exc):
        self._stop.set(); self._thread.join(timeout=5); return False

    def write(self, path):
        Path(path).write_text(''.join(canonical(s) + '\n' for s in self.samples), encoding='utf-8')


def detect_steps(samples, threshold=STEP_SECONDS):
    """Wall-clock steps: consecutive change of (wall - monotonic midpoint) larger than the threshold."""
    steps = []
    offsets = [s['wall_time'] - (s['monotonic_low'] + s['monotonic_high']) / 2 for s in samples]
    for i in range(1, len(samples)):
        delta = offsets[i] - offsets[i - 1]
        if abs(delta) > threshold:
            steps.append({'between_wall_times': [samples[i - 1]['wall_time'], samples[i]['wall_time']], 'offset_change_seconds': delta})
    gaps = [b['monotonic_low'] - a['monotonic_high'] for a, b in zip(samples, samples[1:])]
    return steps, {'sample_count': len(samples), 'max_sample_gap_seconds': max(gaps, default=0.0),
                   'wall_minus_monotonic_range_seconds': (max(offsets) - min(offsets)) if offsets else None,
                   'wall_clock_backwards': any(b['wall_time'] < a['wall_time'] for a, b in zip(samples, samples[1:]))}


def run_interval(part, row):
    if part == 'A': m = row.get('metadata', {}); return m.get('started_at'), m.get('finished_at')
    return row.get('started_at'), row.get('finished_at')


def flag_runs(output, steps):
    """Flag by timestamps only: overlap with a detected step, or |theft handoff error| > 1 s. Never by outcome."""
    output = Path(output); flagged = []
    for part in 'ABC':
        d = output / PARTS[part]
        for row in read_summaries(d):
            timing = (part == 'A' and row.get('scenario') in ('S3', 'S4')) or part == 'C'
            start, end = run_interval(part, row)
            reasons = []
            if timing and start is not None and end is not None:
                for s in steps:
                    lo, hi = s['between_wall_times']
                    if start <= hi and end >= lo: reasons.append('overlaps_wall_clock_step')
                    if reasons: break
            err = row.get('theft_schedule_error_seconds')
            if part == 'A' and timing and isinstance(err, (int, float)) and abs(err) > 1: reasons.append('handoff_error_over_1s')
            if reasons:
                flagged.append({'part': part, 'run_id': row['run_id'], 'uid': uid(part, row), 'timing_run': timing, 'reasons': reasons,
                                'is_rerun': 'rerun_of' in row, 'started_at': start, 'finished_at': end})
    return flagged


# ---------------------------------------------------------------- execution
class Progress:
    def __init__(self, output, planned):
        self.output = Path(output); self.lock = threading.Lock(); self.planned = planned
        self.done = {p: 0 for p in planned}; self.bad = {p: 0 for p in planned}; self.cost = 0.0

    def tick(self, part, summary):
        with self.lock:
            self.done[part] += 1; self.bad[part] += summary.get('status') not in ('completed', 'model_step_limit', 'provider_failure')
            self.cost += float(summary.get('cost_usd') or 0)
            write_json(self.output / 'final-progress.json', {'planned': self.planned, 'finished': self.done, 'not_completed': self.bad,
                                                              'cost_usd_this_collection': self.cost, 'updated_at': time.time()})


def run_part_tasks(part, tasks, pcfg, output, progress, links):
    """Run ``tasks`` (cells) for one part on its own worker pool; returns summaries."""
    out = []
    if not tasks: return out
    destination = Path(output) / PARTS[part]

    def one(cell):
        try: summary = RUNNERS[part](cell, pcfg, destination)
        except Exception as error:  # run functions retain their own failures; this is a last-resort record
            summary = {'status': 'infrastructure_failure', 'error': 'orchestrator: ' + type(error).__name__ + ': ' + str(error), 'run_id': None}
            with links['lock']: (Path(output) / 'orchestrator-crashes.jsonl').open('a', encoding='utf-8').write(canonical({'part': part, 'uid': uid(part, cell), 'error': summary['error']}) + '\n')
        progress.tick(part, summary)
        if summary.get('status') == 'completed' or summary.get('status') in ('model_step_limit', 'provider_failure'):
            print(canonical({'part': part, 'uid_status': summary.get('status'), 'condition': cell.get('condition'), 'scenario': cell.get('scenario')}), flush=True)
        return summary
    with concurrent.futures.ThreadPoolExecutor(max_workers=pcfg.get('concurrency', 1)) as pool:
        for future in concurrent.futures.as_completed([pool.submit(one, c) for c in tasks]): out.append(future.result())
    return out


def pending_cells(part, cells, output):
    """Cells with no usable terminal run yet (resume support)."""
    done = {uid(part, r) for r in read_summaries(Path(output) / PARTS[part]) if r.get('status') not in INFRA[part] and 'rerun_of' not in r}
    return [c for c in cells if uid(part, c) not in done]


def infra_reruns(part, cells, output):
    """One linked rerun for each cell whose only runs are infrastructure failures."""
    rows = read_summaries(Path(output) / PARTS[part]); by = {}
    for r in rows: by.setdefault(uid(part, r), []).append(r)
    redo = []
    for cell in cells:
        runs = by.get(uid(part, cell), [])
        if not runs or any(r.get('status') not in INFRA[part] for r in runs) or any('rerun_of' in r for r in runs): continue
        redo.append(dict(cell, rerun_of=runs[0].get('run_id') or 'unknown'))
    return redo


def run_collection(config, output, resume=False):
    validate_config(config)
    output = Path(output)
    if output.exists() and not resume: raise ValueError('Use a fresh collection directory (or --resume)')
    stages = config.get('stages', [['B', 'C'], ['A']])
    cells = {}
    if not resume:
        from scripts.verify_authorization_runtime import verify as verify_auth
        verification = {'authorization_runtime': verify_auth(), 'binding_runtime': part_c.verify_runtime()}
        verification['passed'] = verification['authorization_runtime']['passed'] and verification['binding_runtime']['passed']
        output.mkdir(parents=True, exist_ok=True); write_json(output / 'runtime-verification.json', verification)
        if not verification['passed']: raise RuntimeError('Runtime bytes in containers differ from source; rebuild first')
        write_json(output / 'config.json', config)
        if config['phase'] == 'full': write_json(output / 'freeze.json', validate_freeze(config))
        for part in 'ABC':
            cells[part] = PREPARE[part](part_config(config, part), output / PARTS[part])
        git = lambda *a: subprocess.run(['git', *a], cwd=ROOT, text=True, capture_output=True).stdout.strip()
        write_json(output / 'final-manifest.json', {'protocol_id': config['protocol_id'], 'created_at': time.time(), 'phase': config['phase'], 'seed': config['seed'],
                   'counts': {p: len(c) for p, c in cells.items()}, 'total': sum(len(c) for c in cells.values()), 'stages': stages,
                   'git_commit': git('rev-parse', 'HEAD'), 'git_dirty_paths': git('status', '--porcelain', '--', 'testbed', 'infra', 'scripts', 'analysis', 'configs').splitlines(),
                   'python': sys.version, 'collection_name': output.name, 'process_id': os.getpid(),
                   'cells': {p: [uid(p, c) for c in cells[p]] for p in cells}})
    else:
        saved = json.loads((output / 'config.json').read_text(encoding='utf-8'))
        if digest(saved) != digest(config): raise ValueError('Resume requires the identical configuration')
        for part in 'ABC':
            pcfg = part_config(config, part)
            cells[part] = {'A': part_a.manifest, 'B': part_b.manifest, 'C': part_c.manifest}[part](pcfg)
    pcfgs = {p: part_config(config, p) for p in 'ABC'}
    progress = Progress(output, {p: len(cells[p]) for p in cells}); links = {'lock': threading.Lock()}
    with ClockMonitor() as monitor, keep_awake():
        for stage in stages:
            threads = []
            for part in stage:
                t = threading.Thread(target=run_part_tasks, args=(part, pending_cells(part, cells[part], output), pcfgs[part], output, progress, links))
                t.start(); threads.append(t)
            for t in threads: t.join()
            for part in stage:  # one linked infrastructure rerun per cell, never selected on outcome
                redo = infra_reruns(part, cells[part], output)
                for row in redo: (output / 'rerun-links.jsonl').open('a', encoding='utf-8').write(canonical({'part': part, 'uid': uid(part, row), 'rerun_of': row['rerun_of'], 'kind': 'infrastructure', 'at': time.time()}) + '\n')
                run_part_tasks(part, redo, pcfgs[part], output, progress, links)
    name = 'clock-monitor.jsonl' if not (output / 'clock-monitor.jsonl').exists() else 'clock-monitor-resume-%d.jsonl' % int(time.time())
    monitor.write(output / name)
    return finalize_quality(output, cells)


def finalize_quality(output, cells=None):
    """Write quality.json from all clock-monitor files and run timestamps (no outcome used)."""
    output = Path(output); steps = []; clock = {'sample_count': 0, 'max_sample_gap_seconds': 0.0, 'wall_minus_monotonic_range_seconds': 0.0, 'wall_clock_backwards': False, 'monitor_files': []}
    for p in sorted(output.glob('clock-monitor*.jsonl')):  # each file is a separately monitored period
        samples = [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines() if line]
        s, c = detect_steps(samples); steps += s
        clock['sample_count'] += c['sample_count']; clock['max_sample_gap_seconds'] = max(clock['max_sample_gap_seconds'], c['max_sample_gap_seconds'])
        clock['wall_minus_monotonic_range_seconds'] = max(clock['wall_minus_monotonic_range_seconds'], c['wall_minus_monotonic_range_seconds'] or 0.0)
        clock['wall_clock_backwards'] = clock['wall_clock_backwards'] or c['wall_clock_backwards']; clock['monitor_files'].append(p.name)
    flagged = flag_runs(output, steps)
    status = {}
    for part in 'ABC':
        rows = read_summaries(output / PARTS[part]); counts = {}
        for r in rows: counts[r.get('status')] = counts.get(r.get('status'), 0) + 1
        status[part] = {'runs_on_disk': len(rows), 'status_counts': counts}
    quality = {'created_at': time.time(), 'clock': clock, 'wall_clock_steps_over_0_5s': steps, 'flagged_runs': flagged,
               'flagged_timing_runs_without_rerun': [f for f in flagged if f['timing_run'] and not f['is_rerun']
                                                      and not any(g['is_rerun'] and g['uid'] == f['uid'] and g['part'] == f['part'] for g in read_rerun_rows(output))],
               'clock_passed': not steps and not clock['wall_clock_backwards'] and clock['max_sample_gap_seconds'] <= 10,
               'runs': status,
               'rule': 'Runs are flagged by timestamps only. Flagged S3/S4 (Part A) and Part C timing runs get exactly one linked rerun; originals are preserved.'}
    write_json(output / 'quality.json', quality)
    return {'quality': quality}


def read_rerun_rows(output):
    rows = []
    for part in 'ABC':
        rows += [dict(r, part=part, uid=uid(part, r), is_rerun=True) for r in read_summaries(Path(output) / PARTS[part]) if 'timing_rerun_of' in r]
    return rows


def timing_reruns(config, output):
    """Prespecified: exactly one linked rerun for each flagged timing run (timestamps only)."""
    validate_config(config); output = Path(output)
    quality = finalize_quality(output)['quality']
    pcfgs = {p: part_config(config, p) for p in 'ABC'}
    todo = {p: [] for p in 'ABC'}
    for f in quality['flagged_runs']:
        if not f['timing_run'] or f['is_rerun']: continue
        part = f['part']; rows = read_summaries(output / PARTS[part])
        original = next(r for r in rows if r['run_id'] == f['run_id'])
        if any(r.get('timing_rerun_of') == f['run_id'] for r in rows): continue
        keys = ('condition', 'scenario', 'ttl_seconds', 'revocation_mode', 'seed', 'pair_id') if part == 'A' else ('cell_id', 'condition', 'replicate', 'ttl_seconds', 'order')
        todo[part].append({**{k: original[k] for k in keys}, 'timing_rerun_of': f['run_id']})
    links = {'lock': threading.Lock()}; progress = Progress(output, {p: len(todo[p]) for p in todo})
    with ClockMonitor() as monitor, keep_awake():
        threads = [threading.Thread(target=run_part_tasks, args=(p, todo[p], pcfgs[p], output, progress, links)) for p in 'ABC' if todo[p]]
        for t in threads: t.start()
        for t in threads: t.join()
    monitor.write(output / ('clock-monitor-timing-reruns-%d.jsonl' % int(time.time())))
    for p in todo:
        for row in todo[p]:
            (output / 'rerun-links.jsonl').open('a', encoding='utf-8').write(canonical({'part': p, 'uid': uid(p, row), 'rerun_of': row['timing_rerun_of'], 'kind': 'timing', 'at': time.time()}) + '\n')
    return {'reruns': {p: len(todo[p]) for p in todo}, **finalize_quality(output)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    for name in ('run', 'timing-reruns', 'quality', 'freeze', 'plan'):
        p = sub.add_parser(name); p.add_argument('--config', default='configs/final-study.json'); p.add_argument('--output')
        if name == 'run': p.add_argument('--resume', action='store_true')
        if name == 'freeze': p.add_argument('--pilot-reference', default='')
    args = parser.parse_args(argv)
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    if args.cmd == 'plan':
        print(json.dumps({p: len(c) for p, c in expected_counts(config).items()})); return 0
    if args.cmd == 'freeze':
        print(json.dumps(make_freeze(args.config, args.pilot_reference), indent=2)); return 0
    if args.cmd == 'quality': finalize_quality(args.output); return 0
    if args.cmd == 'timing-reruns': print(json.dumps(timing_reruns(config, args.output)['reruns'])); return 0
    result = run_collection(config, args.output, args.resume)
    print(json.dumps({'clock_passed': result['quality']['clock_passed'], 'runs': result['quality']['runs']}))
    return 0


if __name__ == '__main__': raise SystemExit(main())
