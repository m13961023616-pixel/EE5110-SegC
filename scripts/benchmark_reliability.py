"""Reproduce four independent performance groups; fail if either task misses 90%."""
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GROUPS = [('iid_pick', 'pick', 20261011, 180, False),
          ('iid_place', 'place', 20261012, 180, False),
          ('balanced_pick', 'pick', 20261101, 120, True),
          ('balanced_place', 'place', 20261102, 120, True)]


def main():
    output = ROOT / 'outputs' / ('reliability_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    summaries = []
    for name, task, seed, count, balanced in GROUPS:
        folder = output / name
        folder.mkdir(parents=True, exist_ok=True)
        command = [sys.executable, str(ROOT / 'main.py'), '--headless', '--trials', str(count),
                   '--seed', str(seed), '--task', task, '--output', str(folder)]
        if balanced:
            command.append('--balanced')
        with (folder / 'console.txt').open('w', encoding='utf-8') as stream:
            subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True)
        paths = list(folder.glob('summary_*.json'))
        assert len(paths) == 1
        summary = json.loads(paths[0].read_text())
        assert summary['trials'] == count
        assert len(summary['per_object']) == 6
        summaries.append(summary)
        print(name, summary['successes'], '/', count, f"{summary['success_rate']:.1%}", flush=True)
    assert len({s['source_sha256'] for s in summaries}) == 1
    pooled = {}
    for s in summaries:
        for name, row in s['per_object'].items():
            total = pooled.setdefault((s['task'], name), [0, 0])
            total[0] += row['successes']
            total[1] += row['trials']
    for (task, name), (success, count) in pooled.items():
        print('Pooled', task, name, f'{success}/{count}', f'{success/count:.1%}')
    print('Evidence:', output)
    passed = all(s['success_rate'] >= .90 for s in summaries)
    passed = passed and all(success / count >= .90 for success, count in pooled.values())
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
