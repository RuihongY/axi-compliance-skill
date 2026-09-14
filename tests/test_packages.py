import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ('axi4-stream-compliance', 'axi4-lite-compliance')


class PackageTests(unittest.TestCase):
    def test_archive_exactly_matches_sources(self):
        for name in SKILLS:
            expected = {p.relative_to(ROOT).as_posix(): p.read_bytes()
                        for p in (ROOT / name).rglob('*')
                        if p.is_file() and '__pycache__' not in p.parts}
            with zipfile.ZipFile(ROOT / (name + '.skill')) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(set(archive.namelist()), set(expected))
                for path, contents in expected.items():
                    self.assertEqual(archive.read(path), contents, path)

    def test_packaged_extractors_run_in_isolation(self):
        for name in SKILLS:
            with tempfile.TemporaryDirectory() as temp:
                with zipfile.ZipFile(ROOT / (name + '.skill')) as archive:
                    archive.extractall(temp)
                rtl = Path(temp) / 'dut.sv'
                rtl.write_text('module dut(input [31:0] WDATA, output [23:0] TDATA); endmodule')
                result = subprocess.run([sys.executable, str(Path(temp) / name / 'scripts/extract_signals.py'), str(rtl)], cwd=temp, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads(result.stdout)
                self.assertNotIn('error', report)
                self.assertFalse(any(n.startswith('CRITICAL') for n in report['notes']))

    def test_eval_cases_have_unique_ids_and_review_criteria(self):
        for name in SKILLS:
            data = json.loads((ROOT / name / 'evals/evals.json').read_text())
            self.assertEqual(data['skill_name'], name)
            cases = data['evals']
            self.assertEqual(len(cases), len({case['id'] for case in cases}))
            for case in cases:
                self.assertTrue(case['prompt'])
                self.assertTrue(case['expected_output'])
                self.assertTrue(case['assertions'])
                for check in case['assertions']:
                    self.assertIn(check['type'], ('contains', 'not_contains', 'contains_any', 'rubric'))


if __name__ == '__main__':
    unittest.main()
