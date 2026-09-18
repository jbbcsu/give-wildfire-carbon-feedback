import unittest

from inspect_peeps_mpi_ssp585_store_metadata import checked_metadata


class MetadataContractTests(unittest.TestCase):
    def test_expected_structure(self):
        row = {'variable': 'pr', 'ensemble': 'r1i1p1f1'}
        document = {'metadata': {
            '.zattrs': {'source_id': 'MPI-ESM1-2-HR', 'experiment_id': 'ssp585',
                        'variant_label': 'r1i1p1f1', 'grid_label': 'gn',
                        'table_id': 'Amon', 'license': 'test license'},
            'pr/.zattrs': {'_ARRAY_DIMENSIONS': ['time', 'lat', 'lon'],
                           'units': 'kg m-2 s-1'},
            'pr/.zarray': {'shape': [1032, 192, 384], 'chunks': [12, 192, 384],
                           'dtype': '<f4'},
            'lat/.zarray': {'shape': [192]}, 'lon/.zarray': {'shape': [384]},
            'time/.zattrs': {'calendar': 'proleptic_gregorian', 'units': 'days since 1850-01-01'}}}
        found = checked_metadata(document, row)
        self.assertEqual(found['uncompressed_chunk_bytes'], 12 * 192 * 384 * 4)
        document['metadata']['pr/.zattrs']['units'] = 'mm/day'
        with self.assertRaises(ValueError):
            checked_metadata(document, row)


if __name__ == '__main__':
    unittest.main()
