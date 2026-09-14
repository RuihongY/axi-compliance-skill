import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / name / 'scripts/check_burst.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AXIBurstTests(unittest.TestCase):
    def setUp(self):
        self.module = load('axi4-full-compliance')

    def run_burst(self, **changes):
        descriptor = dict(addr=0, len=0, size=2, burst=1, data_width=32)
        descriptor.update(changes)
        return self.module.check(descriptor)

    def test_unaligned_last_byte_of_page(self):
        result = self.run_burst(addr=4095, wstrb=[8])
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['addresses'], [4095])
        self.assertEqual(result['allowed_wstrb'], [8])

    def test_next_beat_crosses_page_even_with_zero_strobes(self):
        result = self.run_burst(addr=4095, len=1, wstrb=[0, 0])
        self.assertEqual(result['addresses'], [4095, 4096])
        self.assertTrue(any(e.startswith('B3') for e in result['errors']))

    def test_fixed_does_not_increment(self):
        result = self.run_burst(addr=4095, len=15, burst=0, wstrb=[8] * 16)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['addresses'], [4095] * 16)

    def test_fixed_cannot_have_17_beats(self):
        self.assertEqual(self.run_burst(len=16, burst=0)['status'], 'FAIL')

    def test_incr_256_beats_is_legal(self):
        result = self.run_burst(len=255)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['addresses']), 256)
        self.assertEqual(result['addresses'][-1], 1020)

    def test_wrap_start_is_not_region_aligned(self):
        result = self.run_burst(addr=12, len=3, burst=2)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['addresses'], [12, 0, 4, 8])

    def test_wrap_at_page_end(self):
        result = self.run_burst(addr=4092, len=3, burst=2)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['addresses'], [4092, 4080, 4084, 4088])

    def test_wrap_bad_alignment_and_length(self):
        for changes in [dict(addr=1, len=3), dict(len=2), dict(len=0), dict(len=31)]:
            self.assertEqual(self.run_burst(burst=2, **changes)['status'], 'FAIL')

    def test_narrow_lanes_and_partial_masks(self):
        result = self.run_burst(addr=2, len=3, size=1, data_width=64, wstrb=[4, 32, 0, 3])
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['addresses'], [2, 4, 6, 8])
        self.assertEqual(result['allowed_wstrb'], [12, 48, 192, 3])

    def test_unaligned_strobe_cannot_enable_preceding_byte(self):
        result = self.run_burst(addr=3, wstrb=[15])
        self.assertTrue(any(e.startswith('B5') for e in result['errors']))

    def test_mask_count_and_out_of_bus_bits(self):
        for masks in [[], [15, 15], [16]]:
            self.assertEqual(self.run_burst(wstrb=masks)['status'], 'FAIL')

    def test_transfer_too_wide_and_reserved_encodings(self):
        for change in [dict(size=3), dict(burst=3), dict(len=256), dict(size=-1), dict(data_width=24)]:
            self.assertEqual(self.run_burst(**change)['status'], 'FAIL')

    def test_address_overflow(self):
        self.assertEqual(self.run_burst(addr=252, len=1, addr_width=8)['status'], 'FAIL')

    def test_malformed_inputs(self):
        for descriptor in [[], {}, dict(addr=True, len=0, size=0, burst=1, data_width=32)]:
            with self.assertRaises(ValueError):
                self.module.check(descriptor)
        for masks in ['15', [True], [-1]]:
            with self.assertRaises(ValueError):
                self.run_burst(wstrb=masks)


class AHBBurstTests(unittest.TestCase):
    def setUp(self):
        self.module = load('ahb-compliance')

    def run_burst(self, **changes):
        d = dict(addr=0, size=2, burst=3, data_width=32)
        d.update(changes)
        return self.module.check(d)

    def test_small_ahb_bus_widths_are_legal(self):
        for width, size in [(8, 0), (16, 1)]:
            self.assertEqual(self.run_burst(data_width=width, size=size)['status'], 'PASS')

    def test_all_fixed_encodings(self):
        for burst, count in [(0, 1), (2, 4), (3, 4), (4, 8), (5, 8), (6, 16), (7, 16)]:
            result = self.run_burst(burst=burst)
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(len(result['addresses']), count)

    def test_incr_crosses_1kb(self):
        self.assertEqual(self.run_burst(addr=1016)['status'], 'FAIL')
        self.assertEqual(self.run_burst(addr=1008)['status'], 'PASS')

    def test_wrap_at_1kb_end(self):
        result = self.run_burst(addr=1020, burst=2)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['addresses'], [1020, 1008, 1012, 1016])

    def test_unaligned_is_illegal_unlike_axi(self):
        self.assertEqual(self.run_burst(addr=1, size=1)['status'], 'FAIL')

    def test_narrow_increment_uses_size(self):
        result = self.run_burst(size=1, data_width=64)
        self.assertEqual(result['addresses'], [0, 2, 4, 6])
        self.assertEqual(result['status'], 'PASS')

    def test_incr_requires_count_and_can_restart_at_boundary(self):
        with self.assertRaises(ValueError):
            self.run_burst(burst=1)
        self.assertEqual(self.run_burst(addr=1020, burst=1, beats=1)['status'], 'PASS')
        self.assertEqual(self.run_burst(addr=1024, burst=1, beats=3)['status'], 'PASS')
        self.assertEqual(self.run_burst(addr=1020, burst=1, beats=2)['status'], 'FAIL')

    def test_wrong_fixed_count_is_not_silently_truncated(self):
        self.assertEqual(self.run_burst(beats=3)['status'], 'FAIL')

    def test_bad_bus_size_and_address(self):
        for changes in [dict(data_width=24), dict(size=3), dict(addr=-1), dict(addr=1 << 32), dict(burst=8)]:
            self.assertEqual(self.run_burst(**changes)['status'], 'FAIL')

    def test_malformed_inputs(self):
        for descriptor in [None, {}, dict(addr=0, size=2, burst=3, data_width=True)]:
            with self.assertRaises(ValueError):
                self.module.check(descriptor)


class BurstCLITests(unittest.TestCase):
    def test_packaged_tools_and_exit_codes(self):
        for name, good in [('axi4-full-compliance', dict(addr=12, len=3, size=2, burst=2, data_width=32)),
                           ('ahb-compliance', dict(addr=12, size=2, burst=2, data_width=32))]:
            with tempfile.TemporaryDirectory() as temp:
                with zipfile.ZipFile(ROOT / (name + '.skill')) as archive:
                    archive.extractall(temp)
                script = Path(temp) / name / 'scripts/check_burst.py'
                descriptor = Path(temp) / 'burst.json'
                for data, code in [(good, 0), (dict(good, size=7), 1), ({}, 2), ([], 2)]:
                    descriptor.write_text(json.dumps(data))
                    result = subprocess.run([sys.executable, str(script), str(descriptor)], cwd=temp, capture_output=True, text=True)
                    self.assertEqual(result.returncode, code, result.stderr)
                    self.assertIsInstance(json.loads(result.stdout), dict)
                descriptor.write_text('{invalid')
                result = subprocess.run([sys.executable, str(script), str(descriptor)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn('error', json.loads(result.stdout))
                result = subprocess.run([sys.executable, str(script), str(Path(temp) / 'missing.json')], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
