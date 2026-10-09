"""Reproduce paired clear/barrier planning comparisons; keep every failure."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    'clear_direct': ('clear', 'direct', .22),
    'barrier_direct': ('barrier', 'direct', .22),
    'barrier_rrt': ('barrier', 'rrt', .22),
    'barrier_clearance': ('barrier', 'clearance_rrt', .22),
    'tall_rrt': ('barrier', 'rrt', .28),
    'tall_clearance': ('barrier', 'clearance_rrt', .28),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', nargs='+', choices=CASES, default=list(CASES))
    parser.add_argument('--trials', type=int, default=60)
    parser.add_argument('--seed', type=int, default=20261301)
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/obstacle_benchmark')
    args = parser.parse_args()
    if args.trials < 6 or args.trials % 6:
        parser.error('Use a positive whole number of six-object balanced blocks')
    for name in args.cases:
        scene, planner, height = CASES[name]
        folder = args.output / name
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / 'console.log').open('w', encoding='utf-8') as console:
            subprocess.run([sys.executable, str(ROOT / 'challenge_main.py'), '--headless',
                            '--scene', scene, '--planner', planner, '--height', str(height),
                            '--trials', str(args.trials), '--seed', str(args.seed), '--output', str(folder)],
                           cwd=ROOT, stdout=console, stderr=subprocess.STDOUT, check=True)
        path = max(folder.glob('summary_*.json'), key=lambda p: p.stat().st_mtime_ns)
        summary = json.loads(path.read_text())
        print(name, summary['successes'], '/', summary['trials'], summary['failures'], flush=True)


if __name__ == '__main__':
    main()
