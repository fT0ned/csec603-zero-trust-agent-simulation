"""Hold an idle-sleep request only while collecting; never change the power plan."""
from contextlib import contextmanager
import os

@contextmanager
def keep_awake():
    kernel=None
    if os.name=='nt':
        import ctypes
        kernel=ctypes.windll.kernel32
        kernel.SetThreadExecutionState.argtypes=[ctypes.c_uint]
        kernel.SetThreadExecutionState.restype=ctypes.c_uint
        if not kernel.SetThreadExecutionState(0x80000001):
            raise RuntimeError('Windows refused the temporary idle-sleep prevention request')
    try: yield
    finally:
        if kernel: kernel.SetThreadExecutionState(0x80000000)
