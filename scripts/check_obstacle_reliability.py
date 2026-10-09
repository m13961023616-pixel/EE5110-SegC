"""Audit exact-version paired obstacle reliability evidence and physical gates."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from challenge_main import source_hash
from benchmark_obstacle_reliability import CASES


def reference_hash():
    command = ['git', '-c', 'safe.directory=' + ROOT.as_posix(), '-C', str(ROOT)]
    files = subprocess.check_output(command + ['ls-tree', '-r', '--name-only', 'v1.2.0', 'robot_manipulation/']).decode().splitlines()
    digest = hashlib.sha256()
    for name in ['main.py', 'challenge_main.py', *sorted(f for f in files if f.endswith('.py'))]:
        digest.update(name.encode())
        digest.update(subprocess.check_output(command + ['show', 'v1.2.0:' + name]).replace(b'\r\n', b'\n'))
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, default=ROOT / 'docs/validation/v1.3.0')
    parser.add_argument('--offline', action='store_true', help='Check archived reference hash from the protocol, without Git')
    args = parser.parse_args()
    expected_reference = '52e5e463644bcb02cbd7e06b6dd9bff0a1abf129cf5b187aaa5cf0c6d558ac6a'
    if not args.offline:
        assert reference_hash() == expected_reference
    old_hash, new_hash = expected_reference, source_hash()
    pairs = {}
    control = None
    provenance = None
    for name, (version, height) in CASES.items():
        folder = args.folder / name
        summaries, logs = list(folder.glob('summary_*.json')), list(folder.glob('trials_*.jsonl'))
        assert len(summaries) == len(logs) == 1
        s = json.loads(summaries[0].read_text())
        rows = [json.loads(line) for line in logs[0].read_text().splitlines()]
        assert s['source_sha256'] == (old_hash if version == 'reference' else new_hash)
        assert s['code_version'] == ('1.2.0' if version == 'reference' else '1.3.0')
        assert s['seed'] == 20261401 and len(rows) == s['trials'] == 120
        assert s['successes'] == sum(r['success'] for r in rows)
        assert s['failures'] == dict(Counter(r['failure_stage'] for r in rows if not r['success']))
        assert s['planner'] == ('clearance_rrt' if version == 'reference' else 'robust')
        assert s['scene'] == 'barrier' and abs(s['obstacles'][0]['half_size'][2] * 2 - height) < 1e-12
        configuration = dict(s['config']); configuration.pop('output_dir')
        if control is None:
            control = configuration
        assert configuration == control
        model_versions = {k:s[k] for k in ('python', 'mujoco', 'numpy', 'robot_model_commit', 'dataset_commit')}
        if provenance is None:
            provenance = model_versions
        assert model_versions == provenance
        assert configuration['success_height'] == .08 and configuration['place_tolerance'] == .055
        assert configuration['hold_seconds'] == 1 and configuration['gripper_force_limit'] == 40
        assert Counter(r['object_id'] for r in rows) == {o:20 for o in s['object_pool']}
        for index, r in enumerate(rows, 1):
            assert r['trial_id'] == index and r['scene_seed'] == 20262401 + index
            assert r['planner_seed'] == 20361401 + index
            assert 0 <= r['peak_gripper_force_n'] <= 40 + 1e-6
            if r['success']:
                assert r['min_hold_height_m'] > r['initial_height_m'] + .08
                assert r['lift_success'] and r['bilateral_contact_fraction'] >= .95
                assert r['place_success'] and r['released'] and r['place_table_contact']
                assert r['place_distance_m'] < .055 and r['place_linear_speed_m_s'] < .02
                assert r['barrier_contact_steps'] == 0 and r['max_barrier_penetration_m'] <= .001
        pairs[name] = rows
        print(name, s['successes'], '/', len(rows))
    for suffix in ('22', '28'):
        old, new = pairs['v12_' + suffix], pairs['robust_' + suffix]
        for a, b in zip(old, new):
            assert a['object_id'] == b['object_id'] and a['scene_seed'] == b['scene_seed']
            np.testing.assert_allclose(a['spawn_pose'], b['spawn_pose'], rtol=0, atol=1e-10)
        assert sum(r['success'] for r in new) > sum(r['success'] for r in old), 'No measured improvement'
    print('Verified 480 trials, exact old/current source hashes, matched scenes and unchanged physical gates')


if __name__ == '__main__':
    main()
