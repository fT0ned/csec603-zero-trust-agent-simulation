"""Descriptive resource, asynchronous simulated approval and network-failure evidence."""
from __future__ import annotations

import argparse
import asyncio
import itertools
import json
from pathlib import Path
import random
import subprocess
import time
import threading
import uuid

from analysis.statistics import describe, wilson
from scripts.spire import compose
from testbed.common import ROOT, canonical, write_json
from testbed.final_study import ClockMonitor, detect_steps
from testbed.power import keep_awake
from testbed.extension.fixtures import fixture
from testbed.extension.harness import Actors, Session


class ResourceMonitor:
    def __init__(self, output):
        self.output = Path(output)
        self.stop = self.output / ('.resource-stop-' + uuid.uuid4().hex)
        self.thread = None

    def __enter__(self):
        self.thread = threading.Thread(target=resources, args=(self.output / 'resources.jsonl', self.stop), daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.write_text('collection monitor stopped\n')
        self.thread.join(timeout=45)
        return False


def resources(path, stop_file):
    path, stop_file = Path(path), Path(stop_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    while not stop_file.exists():
        started = time.time()
        process = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{json .}}'], capture_output=True, text=True, timeout=30)
        row = {'wall_time': started, 'monotonic': time.monotonic(), 'observer_seconds': time.time() - started,
               'samples': [json.loads(line) for line in process.stdout.splitlines() if line.startswith('{')], 'exit_code': process.returncode}
        with path.open('a', encoding='utf-8') as stream:
            stream.write(canonical(row) + '\n')
        for _ in range(30):
            if stop_file.exists():
                return
            time.sleep(1)


async def approval_one(delay, abandonment, stamp, fatigue, seed, authorized, rerun_of=None):
    rng = random.Random(seed * 100 + int(authorized))
    start_wall, start = time.time(), time.perf_counter()
    abandoned = rng.random() < abandonment
    rubber_stamped = rng.random() < stamp
    fatigue_flips = rng.random() < fatigue * ((seed - 198000 + 1) / 10)
    await asyncio.sleep(min(delay, .1))
    timeout = delay > .1
    allowed = not (abandoned or timeout) and (rubber_stamped or (not authorized if fatigue_flips else authorized))
    return {'delay_assumption_s': delay, 'timeout_assumption_s': .1, 'abandonment_assumption': abandonment,
            'rubber_stamp_assumption': stamp, 'fatigue_assumption_max': fatigue, 'seed': seed, 'authorized': authorized,
            'abandoned': abandoned, 'timed_out': timeout, 'approved': allowed, 'false_approval': allowed and not authorized,
            'false_denial': not allowed and authorized, 'wait_ms': (time.perf_counter() - start) * 1000,
            'started_at': start_wall, 'finished_at': time.time(), 'rerun_of': rerun_of,
            'evidence_class': 'asynchronous simulated approver; not human behavior'}


def approval(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    grid = list(itertools.product((0, .05, .2), (0, .2), (0, .5), (0, .2), range(198000, 198010)))
    rows = []
    with keep_awake(), ClockMonitor(output / 'clock-monitor.jsonl') as clock:
        for args in grid:
            for authorized in (True, False):
                rows.append(asyncio.run(approval_one(*args, authorized)))
        steps, quality = detect_steps(clock.samples)
        for index, row in list(enumerate(rows)):
            if any(row['started_at'] <= step['between_wall_times'][1] and row['finished_at'] >= step['between_wall_times'][0] for step in steps):
                args = (row['delay_assumption_s'], row['abandonment_assumption'], row['rubber_stamp_assumption'], row['fatigue_assumption_max'], row['seed'], row['authorized'])
                rows.append(asyncio.run(approval_one(*args, rerun_of=index)))
    replaced = {r['rerun_of'] for r in rows if r['rerun_of'] is not None}
    primary = [r for i, r in enumerate(rows) if i not in replaced]
    summary = {'n': len(primary), 'raw_n': len(rows), 'false_approval': wilson(sum(r['false_approval'] for r in primary), sum(not r['authorized'] for r in primary)),
               'false_denial': wilson(sum(r['false_denial'] for r in primary), sum(r['authorized'] for r in primary)),
               'wait_ms': describe([r['wait_ms'] for r in primary]), 'clock_quality': quality, 'steps': steps,
               'interpretation': 'Rates follow assumed parameters and seeded draws; not measured human error/fatigue estimates.'}
    write_json(output / 'rows.json', rows)
    write_json(output / 'summary.json', summary)
    print(canonical(summary))


def network_failure(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    fixed = fixture('benign', 199000, 'crm-handoff')
    result = {'evidence_class': 'scripted network-separated single-PC failure probe', 'started_at': time.time()}
    with keep_awake(), ClockMonitor(output / 'clock-monitor.jsonl') as clock:
        with Actors() as actors:
            session = Session(actors, fixed, 'C3-9449-E')
            session.exchange()
            result['before_failure_allowed'] = session.invoke(fixed['read'])['allowed']
            stopped = time.perf_counter()
            compose('stop', 'extension-pdp')
            try:
                try:
                    session.invoke(fixed['good'])
                    result['outage_refused'] = False
                except RuntimeError:
                    result['outage_refused'] = True
                program = "import urllib.request,json;print(urllib.request.urlopen('http://crm:8000/evidence/" + session.run_id + "').read().decode())"
                state = json.loads(compose('exec', '-T', 'pa', 'python', '-c', program))
                result['outage_write_count'] = len(state['write_calls'])
            finally:
                compose('up', '-d', '--wait', 'extension-pdp', timeout=120)
            result['restart_elapsed_ms'] = (time.perf_counter() - stopped) * 1000
            # This prototype deliberately has no durable STS/run-state restore.
            # Fresh admission after restart is measured rather than pretending
            # the old in-memory credential ledger survived the outage.
            replacement = Session(actors, fixed, 'C3-9449-E')
            replacement.exchange()
            result['fresh_admission_allowed'] = replacement.invoke(fixed['good'])['allowed']
            result['application_evidence'] = replacement.evidence()['independent']['crm']
            replacement.close()
            session.close()
        steps, quality = detect_steps(clock.samples)
    result.update(finished_at=time.time(), steps=steps, clock_quality=quality,
                  limitation='One planned probe; in-memory issuer/run state is lost on PDP restart, requiring fresh admission. Not a high-availability deployment.')
    write_json(output / 'result.json', result)
    print(canonical({k: v for k, v in result.items() if k != 'application_evidence'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('resources', 'approval', 'network-failure'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stop-file', type=Path, default=ROOT / '.runtime/extension-resource-stop')
    args = parser.parse_args()
    if args.command == 'resources':
        resources(args.output, args.stop_file)
    elif args.command == 'approval':
        approval(args.output)
    else:
        network_failure(args.output)
