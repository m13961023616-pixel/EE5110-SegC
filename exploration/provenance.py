"""Fingerprint physical code and frozen experiment/audit definitions."""
import hashlib
from robot_manipulation.config import ROOT


def source_hash():
    digest = hashlib.sha256()
    files = [ROOT/'exploration_main.py', ROOT/'clutter_main.py',
             ROOT/'scripts/benchmark_exploration.py', ROOT/'scripts/check_exploration_evidence.py',
             *sorted((ROOT/'robot_manipulation').glob('*.py')),
             *sorted((ROOT/'exploration').glob('*.py'))]
    for path in files:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes().replace(b'\r\n', b'\n'))
    return digest.hexdigest()
