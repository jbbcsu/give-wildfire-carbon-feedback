import io
from pathlib import Path
import tarfile
import tempfile
import unittest

from extract_peeps_december_pilot import extract_member, INNER_NAME, GMST_INNER_NAME, MAX_MEMBER_BYTES


def archive(name, payload):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w:gz') as bundle:
        info = tarfile.TarInfo(name)
        info.size = len(payload)
        bundle.addfile(info, io.BytesIO(payload))
    return output.getvalue()


class ExtractTests(unittest.TestCase):
    def test_exact_member_only(self):
        target = 'MPI-ESM1-2-HR_ssp585_pr_monthly_patterns_dec.nc'
        payload = b'CDF\x01' + b'abc'
        nested = archive(target, payload)
        outer = archive(INNER_NAME, nested)
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / target
            receipt = extract_member(io.BytesIO(outer), target, destination)
            self.assertEqual(destination.read_bytes(), payload)
            self.assertEqual(receipt['member_bytes'], len(payload))
            self.assertEqual(list(Path(tmp).iterdir()), [destination])

    def test_missing_member_does_not_write(self):
        outer = archive(INNER_NAME, archive('other.nc', b'CDF\x01'))
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / 'target.nc'
            with self.assertRaises(LookupError):
                extract_member(io.BytesIO(outer), 'target.nc', destination)
            self.assertFalse(destination.exists())

    def test_small_paired_gmst_archive(self):
        target = 'MPI-ESM1-2-HR_ssp585_ensemble_avg_tgav.nc'
        payload = b'\x89HDF\r\n\x1a\n' + b'gmst'
        outer = archive(GMST_INNER_NAME, archive(target, payload))
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / target
            receipt = extract_member(io.BytesIO(outer), target, destination, GMST_INNER_NAME)
            self.assertEqual(destination.read_bytes(), payload)
            self.assertEqual(receipt['member_bytes'], len(payload))

    def test_large_member_rejected_before_write(self):
        target = 'large.nc'
        outer = archive(INNER_NAME, archive(target, b'CDF\x01' + b'0' * MAX_MEMBER_BYTES))
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / target
            with self.assertRaises(ValueError):
                extract_member(io.BytesIO(outer), target, destination)
            self.assertFalse(destination.exists())


if __name__ == '__main__':
    unittest.main()
