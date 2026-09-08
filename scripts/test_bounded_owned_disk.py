"""Small synthetic process-monitor tests, not climate inputs or results."""
from pathlib import Path
import sys
import tempfile
import unittest
from run_bounded_job import run

ROOT=Path(__file__).resolve().parents[1]


class OwnedDisk(unittest.TestCase):
    def test_small_owned_output_completes(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);dest=d/'out';dest.mkdir()
            r=run([sys.executable,'-c','from pathlib import Path;Path('+repr(str(dest/'test.txt'))+').write_text("synthetic")'],
                d/'receipt.json',d/'log',128,130,write_paths=[dest],max_new_disk_mib=1)
            self.assertEqual(r['status'],'completed')
            self.assertGreaterEqual(r['sampled_peak_new_disk_bytes'],9)
    def test_owned_disk_limit_stops_child(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);dest=d/'out';dest.mkdir()
            code='from pathlib import Path;import time;Path('+repr(str(dest/'test.bin'))+').write_bytes(b"x"*(3*2**20));time.sleep(2)'
            r=run([sys.executable,'-c',code],d/'receipt.json',d/'log',128,130,
                write_paths=[dest],max_new_disk_mib=1)
            self.assertEqual(r['status'],'owned_disk_budget_exceeded')
            self.assertEqual(r['max_new_disk_mib'],1)
    def test_broad_path_and_missing_cap_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory)
            for kwargs in (dict(write_paths=[ROOT/'data/interim'],max_new_disk_mib=1),dict(write_paths=[d])):
                with self.assertRaises(ValueError):run([sys.executable,'-c','pass'],d/'receipt.json',d/'log',128,130,**kwargs)


if __name__=='__main__':unittest.main()
