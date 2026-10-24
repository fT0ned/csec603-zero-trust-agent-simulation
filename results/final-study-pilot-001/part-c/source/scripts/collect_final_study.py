"""Collect final-study-001 (Parts A, B, C) with continuous host clock monitoring and keep-awake.

  python -m scripts.collect_final_study run --config configs/final-study.json --output results/final-study-001
  python -m scripts.collect_final_study run --config ... --output ... --resume      # after an interruption
  python -m scripts.collect_final_study timing-reruns --config ... --output ...     # prespecified, timestamp-decided
  python -m scripts.collect_final_study quality --output ...
The clock monitor (1 Hz wall vs monotonic) and the sleep inhibitor live inside testbed.final_study.
"""
import sys
from testbed.final_study import main

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
