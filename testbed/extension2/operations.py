"""Nonfatal resource observer; no inference or experimental resampling."""
import json
from pathlib import Path
import subprocess
import threading
import time

from testbed.common import canonical


class ResourceMonitor:
    def __init__(self,output):
        self.path=Path(output)/'resources.jsonl';self.stop=threading.Event()
    def __enter__(self):
        self.thread=threading.Thread(target=self.observe,daemon=True);self.thread.start();return self
    def observe(self):
        while not self.stop.is_set():
            row={'wall_time':time.time(),'monotonic':time.monotonic()}
            try:
                result=subprocess.run(['docker','stats','--no-stream','--format','{{json .}}'],capture_output=True,text=True,encoding='utf-8',timeout=15)
                row.update(samples=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')],exit_code=result.returncode)
            except Exception as exc:
                row.update(samples=[],observer_error=type(exc).__name__)
            with self.path.open('a',encoding='utf-8') as stream:stream.write(canonical(row)+'\n')
            self.stop.wait(30)
    def __exit__(self,*args):
        self.stop.set();self.thread.join(timeout=20)
