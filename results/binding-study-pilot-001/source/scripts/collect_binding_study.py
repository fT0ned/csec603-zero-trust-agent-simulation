"""Collect the binding-response study with continuous host clock evidence."""
import argparse
import json
from pathlib import Path
import threading
import time
from testbed.binding_study import run_batch
from testbed.common import canonical, write_json
from testbed.power import keep_awake


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(); output = Path(args.output)
    if output.exists(): raise ValueError('Use a fresh collection directory')
    samples = []; stopped = threading.Event()
    def monitor():
        while True:
            a = time.monotonic(); wall = time.time(); b = time.monotonic()
            samples.append({'wall_time': wall, 'monotonic_low': a, 'monotonic_high': b})
            if stopped.wait(1): return
    worker = threading.Thread(target=monitor, daemon=True); worker.start()
    try:
        with keep_awake():
            result = run_batch(json.loads(Path(args.config).read_text(encoding='utf-8')), output)
    finally:
        stopped.set(); worker.join(timeout=5)
        if output.exists():
            (output/'clock-monitor.jsonl').write_text(''.join(canonical(s)+'\n' for s in samples), encoding='utf-8')
            offsets = [s['wall_time']-(s['monotonic_low']+s['monotonic_high'])/2 for s in samples]
            drift = max(offsets)-min(offsets) if offsets else None
            backwards = any(b['wall_time'] < a['wall_time'] for a, b in zip(samples, samples[1:]))
            gaps = [b['monotonic_low']-a['monotonic_high'] for a, b in zip(samples, samples[1:])]
            write_json(output/'clock-quality.json', {'passed': len(samples) >= 2 and drift <= .5 and not backwards and max(gaps, default=0) <= 10,
                'sample_count': len(samples), 'wall_minus_monotonic_range_seconds': drift,
                'wall_clock_backwards': backwards, 'maximum_sample_gap_seconds': max(gaps, default=0),
                'scope': 'Continuous host clock continuity; per-container wall clocks bracketed by runtime verification. Durations use monotonic clocks where recorded.'})
    return 0 if not result['remaining_failures'] else 2


if __name__ == '__main__': raise SystemExit(main())
