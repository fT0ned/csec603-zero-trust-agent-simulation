"""One linked rerun for independently diagnosed local-platform transport failure.

The frozen coordinator labels local inference HTTP transport failures as provider
failures. This explicitly recorded infrastructure adjudication uses the unchanged
frozen run function once; it never resamples a model refusal or a vendor error.
"""
import hashlib
import json
from pathlib import Path
import time
import uuid

from testbed.common import ROOT, write_json
from testbed.extension.harness import Actors
from testbed.extension.operations import ResourceMonitor
from testbed.extension.study import CONFIG, clock_evidence, run_one, verify_freeze, verify_local_models
from testbed.final_study import ClockMonitor
from testbed.power import keep_awake


def main():
    output = ROOT / 'results/extension-study-001'
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    verify_freeze(config)
    verify_local_models(config)
    queue = json.loads((output / 'manual-platform-rerun-queue.json').read_text(encoding='utf-8'))
    planned = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    rows = [json.loads(p.read_text(encoding='utf-8')) for p in output.glob('runs/*/summary.json')]
    if (output / 'quality.json').exists() and not (output / 'quality-before-manual-platform-rerun.json').exists():
        (output / 'quality-before-manual-platform-rerun.json').write_bytes((output / 'quality.json').read_bytes())
    results = []
    with keep_awake(), ClockMonitor(output / ('clock-monitor-' + uuid.uuid4().hex + '.jsonl')), ResourceMonitor(output):
        with Actors() as actors:
            write_json(output / 'manual-rerun-identities.json', {'identities': actors.public(), 'issuance_ms': actors.issuance_ms})
            for cid in queue['cells']:
                existing = [r for r in rows if r['cell_id'] == cid and r.get('rerun_of')]
                if existing:
                    results.extend(existing)
                    continue
                original = next(r for r in rows if r['cell_id'] == cid)
                if original.get('error_category') != 'provider_transport_error' or not original['model'].startswith('qwen'):
                    raise ValueError('Only documented local platform transport failure is eligible')
                cell = next(c for c in planned if c['cell_id'] == cid)
                result = run_one(cell, config, output, actors, linked=original['run_key'], rerun_reason='independently_verified_local_platform_outage')
                results.append(result)
    steps, clock_quality = clock_evidence(output)
    quality = json.loads((output / 'quality.json').read_text(encoding='utf-8'))
    quality.update(steps=steps, clock_quality=clock_quality, manual_platform_reruns=[r['run_key'] for r in results],
                   platform_outage_reference='platform-outage.json', resource_sampling_gap='Docker observer exited on outage timeout; resumed collector appended new frames.')
    write_json(output / 'quality.json', quality)
    adjudications = json.loads((output / 'adjudications.json').read_text(encoding='utf-8'))
    for result in results:
        entry = adjudications[result['cell_id']]
        entry['manual_linked_rerun_pending'] = False
        entry['linked_rerun'] = result['run_key']
        entry['linked_rerun_status'] = result['status']
    write_json(output / 'adjudications.json', adjudications)
    print(json.dumps([{'cell_id':r['cell_id'],'status':r['status'],'rerun_of':r['rerun_of']} for r in results]))


if __name__ == '__main__':
    main()
