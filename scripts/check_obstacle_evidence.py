"""Audit frozen challenge results and paired physical-scene comparisons."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from challenge_main import source_hash
from benchmark_obstacles import CASES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, default=ROOT / 'docs/validation/v1.2.0')
    args = parser.parse_args()
    reference = None
    for name, (scene, planner, height) in CASES.items():
        folder = args.folder / name
        summaries, logs = list(folder.glob('summary_*.json')), list(folder.glob('trials_*.jsonl'))
        assert len(summaries) == len(logs) == 1
        summary = json.loads(summaries[0].read_text())
        rows = [json.loads(line) for line in logs[0].read_text().splitlines()]
        assert summary['source_sha256'] == source_hash(), 'Current challenge source differs from frozen evidence'
        assert summary['seed'] == 20261301 and summary['trials'] == len(rows) == 60
        assert summary['planner'] == planner and summary['scene'] == scene
        assert summary['successes'] == sum(r['success'] for r in rows)
        assert summary['failures'] == dict(Counter(r['failure_stage'] for r in rows if not r['success']))
        assert Counter(r['object_id'] for r in rows) == {x: 10 for x in summary['object_pool']}
        c = summary['config']
        assert c['success_height'] == .08 and c['hold_seconds'] == 1 and c['place_tolerance'] == .055
        assert c['place_xy'] == [.48, .30] and c['spawn_y'] == [-.10, .06]
        assert c['gripper_force_limit'] == 40 and c['grip_preload'] == 16
        if scene == 'barrier':
            wall = summary['obstacles'][0]
            assert abs(wall['center'][2] + wall['half_size'][2] - height) < 1e-12
        for index, row in enumerate(rows, 1):
            assert row['trial_id'] == index and row['scene_seed'] == summary['seed'] + 1000 + index
            assert row['planner_seed'] == summary['seed'] + 100000 + index
            assert 0 <= row['peak_gripper_force_n'] <= 40 + 1e-6
            if row['success']:
                assert row['lift_success'] and row['bilateral_contact_fraction'] >= .95
                assert row['min_hold_height_m'] > row['initial_height_m'] + .08
                assert row['place_success'] and row['released'] and row['place_table_contact']
                assert row['place_distance_m'] < .055 and row['place_linear_speed_m_s'] < .02
                assert row['barrier_contact_steps'] == 0 and row['max_barrier_penetration_m'] <= .001
        if reference is None:
            reference = rows
        else:
            for a, b in zip(reference, rows):
                assert a['object_id'] == b['object_id'] and a['scene_seed'] == b['scene_seed']
                np.testing.assert_allclose(a['spawn_pose'], b['spawn_pose'], atol=1e-10, rtol=0)
        print(name, summary['successes'], '/', len(rows))
    print('Verified 360 paired scenes, frozen source, original physical thresholds and all failures')


if __name__ == '__main__':
    main()
