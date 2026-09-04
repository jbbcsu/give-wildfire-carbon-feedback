"""Small real-process tests; maximum deliberate allocation is 64 MiB."""
from pathlib import Path
import sys
import tempfile
from run_bounded_job import run

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    def check(name, code, **kwargs):
        return run([sys.executable, '-c', code], root / (name+'.json'),
                   root / (name+'.log'), min_free_gib=0, interval=0.05, **kwargs)
    assert check('success', 'print(123)')['status'] == 'completed'
    assert check('failure', 'raise SystemExit(3)')['returncode'] == 3
    assert check('memory', 'import time; a=bytearray(64*1024*1024); time.sleep(5)',
                 max_mib=40)['status'] == 'memory_budget_exceeded'
    child = 'import time; a=bytearray(64*1024*1024); time.sleep(5)'
    assert check('descendant',
                 'import subprocess,sys; subprocess.run([sys.executable,"-c",'+repr(child)+'])',
                 max_mib=50)['status'] == 'memory_budget_exceeded'
    assert check('log', 'import time; print("x"*200000); time.sleep(5)',
                 max_log_mib=0.1)['status'] == 'log_budget_exceeded'
    try:
        run([sys.executable, '-c', 'raise Exception("must not run")'],
            root/'disk.json', root/'disk.log', min_free_gib=1e9)
    except RuntimeError:
        assert not (root/'disk.log').exists()
    else:
        raise AssertionError('disk check failed')
print('process group, memory, log, disk and exit-code tests passed')
