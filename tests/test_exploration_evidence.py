"""Reject fake deformation, scene resets and force-limit violations in topic evidence."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import check_exploration_evidence as checker


class ExplorationEvidenceChecks(unittest.TestCase):
    def reject(self,group,corrupt):
        evidence=ROOT/'docs/validation/v3.0.0'
        original=checker.load_case
        with tempfile.TemporaryDirectory(dir=ROOT/'outputs') as temporary:
            folder=Path(temporary)
            (folder/'protocol.json').write_bytes((evidence/'protocol.json').read_bytes())
            def loader(path):
                summary,rows=original(evidence/path.name)
                if path.name==group:corrupt(rows[0])
                return summary,rows
            with patch.object(checker,'load_case',side_effect=loader),redirect_stdout(io.StringIO()):
                with self.assertRaises(ValueError):checker.audit(folder)

    def test_rigid_placeholder_cannot_claim_deformable_success(self):
        self.reject('soft_adaptive',lambda row:row.update(physical_model='rigid_box'))

    def test_recovery_cannot_reset_the_scene(self):
        self.reject('recovery_retry',lambda row:row.update(reset_count=2))

    def test_force_limit_cannot_be_hidden(self):
        self.reject('force_adaptive',lambda row:row.update(peak_actuator_force_n=41.))


if __name__=='__main__':unittest.main()
