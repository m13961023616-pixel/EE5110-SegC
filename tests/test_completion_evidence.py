"""The final evidence audit must reject stale source and corrupted physical gates."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_completion_evidence as checker


class EvidenceRejectionChecks(unittest.TestCase):
    def check_corruption(self, corruption):
        evidence = ROOT / 'docs/validation/v2.1.0'
        protocol = json.loads((evidence / 'protocol.json').read_text(encoding='utf-8'))
        original_load = checker.load_case
        (ROOT / 'outputs').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'outputs') as temporary:
            folder = Path(temporary)
            (folder / 'protocol.json').write_text(json.dumps(protocol), encoding='utf-8')
            def load_case(path):
                summary, rows = original_load(evidence / path.name)
                if path.name == 'baseline_clutter':
                    corruption(rows[0])
                return summary, rows
            with patch.object(checker, 'load_case', side_effect=load_case), redirect_stdout(io.StringIO()):
                with self.assertRaises(ValueError):
                    checker.audit(folder)

    def test_force_limit_cannot_be_hidden_by_a_success_flag(self):
        self.check_corruption(lambda row: row.update(peak_gripper_force_n=41.))

    def test_unsafe_contact_cannot_be_hidden_by_a_success_flag(self):
        def corrupt(row):
            row['scene_metrics']['unsafe_contact_steps'] = 1
        self.check_corruption(corrupt)

    def test_stale_source_fingerprint_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Source does not match'):
            checker.audit(ROOT / 'docs/validation/v2.1.0', expected_hash='0' * 64)


if __name__ == '__main__':
    unittest.main()
