"""Synthetic scheduler integration tests; never fetch climate or fit outcomes."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run_us_paired_regional_chain as chain


class ChainTests(unittest.TestCase):
    def fixture(self, root):
        for b in ('south', 'central', 'north'):
            for s in ('obsclim', 'counterclim'):
                for v in ('pr', 'tas', 'tasmax'):
                    for y in (1981, 1991, 2001):
                        d = root/f'data/interim/us_{b}_{s}_{v}_{y}_20260908'
                        d.mkdir(parents=True)
                        (d/'receipt.json').write_text(json.dumps({'status': 'regional_paired_climate_content_validated'}))

    def execute(self, root, fail=False):
        calls = []
        def job_paths(stem):
            return root/'resource.json', root/'log.txt', root/'scratch'
        def run(command, *args, **kwargs):
            calls.append(command[1])
            if command[1] == 'scripts/build_us_regional_county_climate.py':
                out = Path(command[-1])
                out.mkdir()
                if fail:
                    return {'status': 'command_failed'}
                (out/'receipt.json').write_text(json.dumps({'status': 'us_regional_county_climate_inputs_validated'}))
            elif command[1] == 'scripts/compare_us_regional_county_climate.py':
                Path(command[-1]).write_text(json.dumps({'status': 'us_regional_county_climate_comparison_validated'}))
            return {'status': 'completed'}
        with patch.object(chain, 'ROOT', root), patch.object(chain, 'fresh_job', job_paths), patch.object(chain, 'run', run), \
                patch.object(chain.subprocess, 'run') as acquisition, patch.object(chain.sys, 'argv', ['chain', '--max-hours', '1']):
            if fail:
                with self.assertRaisesRegex(RuntimeError, 'bounded chain step failed'):
                    chain.main()
            else:
                chain.main()
            acquisition.assert_not_called()
        state = json.loads((root/'data/interim/us_paired_regional_chain_20260908/state.json').read_text())
        return calls, state

    def test_immediate_stage_chaining(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            calls, state = self.execute(root)
            self.assertEqual(calls, ['scripts/test_us_regional_county_features.py', 'scripts/build_us_regional_county_climate.py',
                                    'scripts/test_us_county_climate_comparison.py', 'scripts/compare_us_regional_county_climate.py'])
            self.assertEqual(state['stage'], 'climate_inputs_and_comparison_complete_review_required')
            self.assertFalse(state['crop_yield_estimated'])

    def test_failure_stops_next_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            calls, state = self.execute(root, fail=True)
            self.assertEqual(len(calls), 2)
            self.assertEqual(state['stage'], 'stopped_preserved_for_review')


if __name__ == '__main__':
    unittest.main()
