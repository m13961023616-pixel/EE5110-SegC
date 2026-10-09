"""Audit frozen-source results, all failures, unchanged criteria and 90% gates."""
from collections import Counter
import hashlib
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
GROUPS = [('iid_pick', 'pick', 20261011, 180, False),
          ('iid_place', 'place', 20261012, 180, False),
          ('balanced_pick', 'pick', 20261101, 120, True),
          ('balanced_place', 'place', 20261102, 120, True)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-ref', help='Audit historical evidence against an explicit Git revision')
    args = parser.parse_args()
    digest = hashlib.sha256()
    if args.source_ref:
        command = ['git', '-c', 'safe.directory=' + ROOT.as_posix(), '-C', str(ROOT)]
        listing = subprocess.check_output(command + ['ls-tree', '-r', '--name-only', args.source_ref, 'robot_manipulation/']).decode().splitlines()
        paths = ['main.py', *sorted(p for p in listing if p.endswith('.py'))]
        for path in paths:
            digest.update(path.encode())
            digest.update(subprocess.check_output(command + ['show', args.source_ref + ':' + path]).replace(b'\r\n', b'\n'))
        print('Historical source revision:', args.source_ref)
    else:
        for path in [ROOT / 'main.py', *sorted((ROOT / 'robot_manipulation').glob('*.py'))]:
            digest.update(path.relative_to(ROOT).as_posix().encode())
            digest.update(path.read_bytes().replace(b'\r\n', b'\n'))
    pooled = {}
    total = 0
    for group, task, seed, count, balanced in GROUPS:
        folder = ROOT / 'docs/validation/v1.1.0' / group
        summaries = list(folder.glob('summary_*.json'))
        trials = list(folder.glob('trials_*.jsonl'))
        assert len(summaries) == len(trials) == 1
        s = json.loads(summaries[0].read_text())
        rows = [json.loads(line) for line in trials[0].read_text().splitlines()]
        assert s['source_sha256'] == digest.hexdigest(), 'Source changed: regenerate performance evidence'
        assert s['task'] == task and s['seed'] == seed and s['trials'] == len(rows) == count
        assert s['sampling'] == ('balanced_shuffled_blocks' if balanced else 'iid_uniform')
        assert len(s['per_object']) == len(s['object_pool']) == 6
        assert sum(r['success'] for r in rows) == s['successes']
        assert dict(Counter(r['failure_stage'] for r in rows if not r['success'])) == s['failures']
        assert abs(s['success_rate'] - s['successes'] / count) < 1e-12
        assert s['success_rate'] >= .90, group
        config = s['config']
        assert config['success_height'] == .08 and config['hold_seconds'] == 1.
        assert config['place_tolerance'] == .055 and config['gripper_force_limit'] == 40.
        assert [r['trial_id'] for r in rows] == list(range(1, count + 1))
        if balanced:
            for start in range(0, count, 6):
                assert {r['object_id'] for r in rows[start:start + 6]} == set(s['object_pool'])
        for r in rows:
            assert r['task'] == task and r['object_id'] in s['object_pool']
            assert 0 <= r['peak_gripper_force_n'] <= 40 + 1e-6
            pair = pooled.setdefault((task, r['object_id']), [0, 0])
            pair[0] += r['success']
            pair[1] += 1
            if r['success']:
                assert r['lift_success'] and r['bilateral_contact_fraction'] >= .95
                assert r['min_hold_height_m'] > r['initial_height_m'] + .08
                if task == 'place':
                    assert r['place_success'] and r['released'] and r['place_table_contact']
                    assert r['place_distance_m'] < .055 and r['place_linear_speed_m_s'] < .02
        print(group, s['successes'], '/', count)
        total += count
    assert all(success / count >= .90 for success, count in pooled.values())
    print('Verified:', total, 'scenes, matching source, all failures, force bounds and 90% gates')


if __name__ == '__main__':
    main()
