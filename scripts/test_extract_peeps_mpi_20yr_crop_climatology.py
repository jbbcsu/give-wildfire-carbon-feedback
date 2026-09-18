import unittest

from extract_peeps_mpi_20yr_crop_climatology import selected_months


class ChunkSelectionTests(unittest.TestCase):
    def test_r1_time_chunks(self):
        early = selected_months(600, 0)
        late = selected_months(600, 1)
        self.assertEqual(len(early), 240)
        self.assertEqual(len(late), 240)
        self.assertEqual(early[0][:3], ("early", 2015, 1))
        self.assertEqual(late[-1][:3], ("late", 2100, 12))

    def test_r2_cross_chunk_periods(self):
        chunks = {i: selected_months(235, i) for i in (0, 1, 3, 4)}
        self.assertEqual(sum(len(v) for v in chunks.values()), 480)
        self.assertEqual(len(chunks[0]), 235)
        self.assertEqual(len(chunks[1]), 5)
        self.assertEqual(sum(p == "late" for v in chunks.values() for p, *_ in v), 240)
        self.assertEqual(len(chunks[4]), 92)


if __name__ == "__main__":
    unittest.main()
