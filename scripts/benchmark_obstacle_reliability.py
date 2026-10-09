"""Compare exact v1.2.0 source with the improved planner on identical scenes."""
import argparse
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
CASES = {'v12_22': ('reference', .22), 'robust_22': ('current', .22),
         'v12_28': ('reference', .28), 'robust_28': ('current', .28)}
REFERENCE = ROOT / 'outputs/v1.2.0_reference'


def prepare_reference():
    marker = REFERENCE / 'snapshot.json'
    if marker.exists():
        return
    command = ['git', '-c', 'safe.directory=' + ROOT.as_posix(), '-C', str(ROOT)]
    payload = subprocess.check_output(command + ['archive', 'v1.2.0', 'main.py', 'challenge_main.py', 'robot_manipulation'])
    REFERENCE.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
        archive.extractall(REFERENCE, filter='data')
    shutil.copytree(ROOT / 'assets', REFERENCE / 'assets', dirs_exist_ok=True)
    marker.write_text(json.dumps({'ref': 'v1.2.0', 'commit': subprocess.check_output(command + ['rev-parse', 'v1.2.0^{}']).decode().strip()}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', nargs='+', choices=CASES, default=list(CASES))
    parser.add_argument('--trials', type=int, default=120)
    parser.add_argument('--seed', type=int, default=20261401)
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/obstacle_reliability')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if args.trials < 6 or args.trials % 6:
        parser.error('Use whole six-object balanced blocks')
    prepare_reference()
    if args.prepare_only:
        print(REFERENCE)
        return
    for name in args.cases:
        source, height = CASES[name]
        entry = (REFERENCE if source == 'reference' else ROOT) / 'challenge_main.py'
        folder = args.output.resolve() / name
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / 'console.log').open('w', encoding='utf-8') as console:
            subprocess.run([sys.executable, str(entry), '--headless', '--scene', 'barrier',
                            '--planner', 'clearance_rrt' if source == 'reference' else 'robust',
                            '--height', str(height), '--seed', str(args.seed), '--trials', str(args.trials),
                            '--output', str(folder)], cwd=ROOT, stdout=console, stderr=subprocess.STDOUT, check=True)
        summary = json.loads(max(folder.glob('summary_*.json'), key=lambda p:p.stat().st_mtime_ns).read_text())
        print(name, summary['successes'], '/', summary['trials'], summary['failures'], flush=True)


if __name__ == '__main__':
    main()
