import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

from extract_peeps_full_month_mpi import extract_stream


def archive(members):
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode='w:gz') as tar:
        for name, payload in members:
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
    return result.getvalue()


class FullMonthTests(unittest.TestCase):
    def test_nested_stream_and_whole_md5(self):
        months = ('jan', 'feb')
        outer_items = []
        for month in months:
            name = f'MPI-ESM1-2-HR_ssp585_pr_monthly_patterns_{month}.nc'
            nested = archive([('unrelated.nc', b'CDF\x01x'),
                              (name, b'\x89HDF\r\n\x1a\n' + month.encode())])
            outer_items.append((f'outputs/{month}_patterns.tar.gz', nested))
        data = archive(outer_items)
        with tempfile.TemporaryDirectory() as tmp:
            result = extract_stream(io.BytesIO(data), tmp, months,
                                    len(data), hashlib.md5(data).hexdigest())
            self.assertEqual(result['selected_months'], list(months))
            self.assertEqual(len(list(Path(tmp).glob('*.nc'))), 2)
            self.assertEqual(result['outer_archive_bytes'], len(data))

    def test_bad_outer_hash_rejected(self):
        name = 'MPI-ESM1-2-HR_ssp585_pr_monthly_patterns_jan.nc'
        data = archive([('outputs/jan_patterns.tar.gz', archive([(name, b'CDF\x01x')]))])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                extract_stream(io.BytesIO(data), tmp, ('jan',), len(data), '0' * 32)


if __name__ == '__main__':
    unittest.main()
