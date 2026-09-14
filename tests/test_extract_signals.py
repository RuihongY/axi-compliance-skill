"""Observable extractor regressions, run without third-party dependencies."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    path = ROOT / name / 'scripts/extract_signals.py'
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExtractorTests(unittest.TestCase):
    def setUp(self):
        self.modules = [load('axi4-stream-compliance'), load('axi4-lite-compliance')]
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.rtl = Path(self.temp.name) / 'dut.sv'

    def test_nonzero_and_ascending_ranges(self):
        for module in self.modules:
            for expr, width in [('31:8', 24), ('0:23', 24), ('7:7', 1), ('W-1:8', 24), ('W/8-1:0', 4)]:
                with self.subTest(module=module.__name__, expr=expr):
                    self.assertEqual(module.resolve_width(expr, {'W': 32}), width)

    def test_unsupported_expressions_stay_unknown(self):
        for module in self.modules:
            for expr in ['31:0 + OFFSET', 'W-1:0 junk', 'foo():0', 'W/0-1:0', 'MISSING-1:0']:
                with self.subTest(expr=expr):
                    self.assertIsNone(module.resolve_width(expr, {'W': 32}))

    def test_comments_do_not_create_ports_or_parameters(self):
        self.rtl.write_text('''// input [11:0] TDATA; parameter W = 12;
/* input [15:0] WDATA; */
module dut(output [23:0] TDATA, input [31:0] WDATA);
initial $display("input [7:0] TKEEP;");
endmodule
''')
        axis, lite = [m.analyze(str(self.rtl)) for m in self.modules]
        self.assertEqual(axis['axis_signals']['TDATA']['width'], 24)
        self.assertNotIn('TKEEP', axis['axis_signals'])
        self.assertEqual(lite['channels']['W']['WDATA']['width'], 32)
        for result in (axis, lite):
            self.assertEqual(result['parameters'], {})

    def test_based_or_expression_parameters_are_not_decimal_prefixes(self):
        self.rtl.write_text("parameter W = 32'h10; parameter N = 32*2; parameter D = 24; output [W-1:0] TDATA;")
        for module in self.modules:
            self.assertEqual(module.analyze(str(self.rtl))['parameters'], {'D': 24})

    def test_24_bit_stream_is_legal(self):
        self.rtl.write_text('module dut(output [23:0] TDATA, output [2:0] TKEEP); endmodule')
        result = self.modules[0].analyze(str(self.rtl))
        self.assertTrue(result['quick_checks']['tdata_byte_aligned'])
        self.assertTrue(result['quick_checks']['tkeep_matches_tdata_bytes'])
        self.assertFalse(any(n.startswith('CRITICAL') for n in result['notes']))

    def test_bad_width_is_still_detected(self):
        self.rtl.write_text('module dut(output [11:0] TDATA, input [15:0] WDATA); endmodule')
        for module in self.modules:
            self.assertTrue(any(n.startswith('CRITICAL W1') for n in module.analyze(str(self.rtl))['notes']))

    def test_valid_reset_is_not_proven_by_nearby_assignment(self):
        self.rtl.write_text("module dut(output reg TVALID); always @(posedge ACLK) if (ARESETn) TVALID <= 1'b0; endmodule")
        axis = self.modules[0].analyze(str(self.rtl))
        self.assertIsNone(axis['reset']['tvalid_cleared_in_reset'])
        for module in self.modules:
            self.assertNotEqual(module.analyze(str(self.rtl))['reset']['polarity'], 'active_high')

    def test_always_ff_async_reset_detection(self):
        self.rtl.write_text("always_ff @(posedge ACLK or negedge ARESETn) if (!ARESETn) TVALID <= 0;")
        for module in self.modules:
            self.assertEqual(module.analyze(str(self.rtl))['reset']['style'], 'async')

    def test_id_reflection_is_not_automatically_a_violation(self):
        self.rtl.write_text('module dut(input [3:0] AWID, output [3:0] BID); endmodule')
        result = self.modules[1].analyze(str(self.rtl))
        self.assertEqual(set(result['full_axi_intrusions']), {'AWID', 'BID'})
        self.assertFalse(any(n.startswith('CRITICAL X1') for n in result['notes']))

    def test_cli_reports_unreadable_inputs_as_errors(self):
        for module in self.modules:
            for path in [self.rtl, self.rtl.parent]:
                result = subprocess.run([sys.executable, module.__file__, str(path)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('error', json.loads(result.stdout))


if __name__ == '__main__':
    unittest.main()
