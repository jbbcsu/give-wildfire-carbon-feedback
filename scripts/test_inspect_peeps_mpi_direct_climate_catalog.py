import unittest

from inspect_peeps_mpi_direct_climate_catalog import selected_row


class MPISelectionTests(unittest.TestCase):
    def test_exact_source_and_domain(self):
        row = {'model': 'MPI-ESM1-2-HR', 'experiment': 'ssp585',
               'variable': 'pr', 'domain': 'Amon'}
        self.assertTrue(selected_row(row))
        self.assertFalse(selected_row({**row, 'domain': 'day'}))
        self.assertFalse(selected_row({**row, 'model': 'GFDL-ESM4'}))
        self.assertFalse(selected_row({**row, 'experiment': 'ssp126'}))


if __name__ == '__main__':
    unittest.main()
