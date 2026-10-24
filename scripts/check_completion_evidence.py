"""Audit all new paired episodes; recompute outcomes and comparisons."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
from statistics import mean
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from clutter_main import source_hash, TARGETS
from robot_manipulation.evaluation import wilson_interval
from benchmark_completion import CASES


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def load_case(folder):
    logs, summaries = list(folder.glob('trials_*.jsonl')), list(folder.glob('summary_*.json'))
    require(len(logs) == len(summaries) == 1, f'{folder}: require one complete run')
    return json.loads(summaries[0].read_text(encoding='utf-8')), [
        json.loads(line) for line in logs[0].read_text(encoding='utf-8').splitlines()]


def scene_safe(metrics):
    return (metrics['unsafe_contact_steps'] == 0 and metrics['distractor_max_displacement_m'] <= .02
            and metrics['max_target_penetration_m'] <= .001)


def audit(folder, expected_hash=None):
    protocol = json.loads((folder / 'protocol.json').read_text(encoding='utf-8'))
    require(protocol['completed'], 'Experiment is incomplete')
    require(protocol['version'] == '2.1.0' and protocol['mode'] == 'active', 'Wrong protocol')
    expected_cases = {n: {'scene': s, 'grasps': g, 'trials': c} for n, (s, g, c) in CASES.items()}
    require(protocol['cases'] == expected_cases, 'Sample counts or groups differ from the frozen design')
    require(protocol['success_gates'] == {'lift_m': .08, 'hold_s': 1., 'bilateral_fraction': .95,
            'place_m': .055, 'speed_m_s': .02, 'force_n': 40., 'neighbor_m': .02,
            'target_penetration_m': .001, 'unsafe_contact_steps': 0}, 'Changed physical gates')
    expected_hash = expected_hash or source_hash()
    require(protocol['source_sha256'] == expected_hash, 'Source does not match frozen evidence')
    groups, result, common_config, provenance = {}, {}, None, None
    seed = protocol['seed']
    require(seed != protocol['development_seed'], 'Evaluation seed was used for development')
    for name, (scene, grasps, count) in CASES.items():
        summary, rows = load_case(folder / name)
        require(summary['source_sha256'] == expected_hash, f'{name}: source mismatch')
        require(summary['code_version'] == '2.1.0' and summary['seed'] == seed, f'{name}: version/seed')
        require(summary['mode'] == 'active' and summary['scene'] == scene and summary['grasp_strategy'] == grasps,
                f'{name}: algorithm/scene mismatch')
        require(summary['trials'] == len(rows) == count, f'{name}: incomplete episodes')
        require(summary['successes'] == sum(r['success'] for r in rows), f'{name}: count mismatch')
        require(summary['failures'] == dict(Counter(r['failure_stage'] for r in rows if not r['success'])),
                f'{name}: omitted failures')
        require(Counter(r['object_id'] for r in rows) == {o: count // 3 for o in TARGETS}, f'{name}: balance')
        require(summary['maximum_attempts'] == 1, f'{name}: confounded by retries')
        require(summary['maximum_additional_candidates'] == (16 if grasps == 'local' else 0), f'{name}: candidate budget')
        config = dict(summary['config']); config.pop('output_dir')
        if common_config is None:
            common_config = config
        require(config == common_config, f'{name}: configuration changed')
        require(config['success_height'] == .08 and config['hold_seconds'] == 1.
                and config['place_tolerance'] == .055 and config['gripper_force_limit'] == 40.
                and config['max_joint_speed'] == .5 and config['max_joint_acceleration'] == 2., 'Relaxed thresholds')
        versions = {k: summary[k] for k in ('python', 'numpy', 'mujoco', 'dataset_commit', 'robot_model_commit', 'sensor')}
        if provenance is None:
            provenance = versions
        require(versions == provenance, f'{name}: changed dependencies/assets/sensor')
        require(summary['sensor']['dropout'] == .98 and summary['sensor']['permanent_dropout'] == .10, 'Sensor changed')
        require(summary['distractor_count'] == (3 if scene == 'clutter' else 5)
                and len(summary['obstacles']) == 3, f'{name}: scene difficulty changed')
        for i, row in enumerate(rows, 1):
            require(row['trial_id'] == i and row['scene_seed'] == seed + 1000 + i
                    and row['sensor_seed'] == seed + 100000 + i and row['planner_seed'] == seed + 200000 + i,
                    f'{name}/{i}: seed stream changed')
            require(row['reset_count'] == row['attempt_count'] == len(row['attempts']) == 1, f'{name}/{i}: resampled scene')
            require(0 <= row['peak_gripper_force_n'] <= 40 + 1e-6, f'{name}/{i}: force bound')
            initial = row['scene_metrics']['initial_scene']
            require(len(initial) == summary['distractor_count'] + 1, f'{name}/{i}: missing neighbors')
            np.testing.assert_array_equal(initial[row['object_id']], row['spawn_pose'])
            attempt = row['attempts'][0]
            require(attempt['peak_gripper_force_n'] == row['peak_gripper_force_n'], 'Attempt force differs from episode')
            require(not row['recovery_actions'], 'Single-attempt ablation contains recovery actions')
            require(row['first_attempt_success'] == (attempt['success'] and scene_safe(attempt['scene_metrics'])), 'Incorrect scene outcome')
            require(row['first_attempt_success'] == row['success'], f'{name}/{i}: inconsistent outcome')
            require(attempt['scene_metrics']['scene_resets'] == i, f'{name}/{i}: reset count')
            require(0 < row['observed_frames'] == attempt['sensing']['used_frames'] <= 64, f'{name}/{i}: sensor budget')
            require(attempt['sensing']['segmentation'] == 'ideal_simulation_instance_mask', 'Unreported segmentation')
            require(row.get('estimated_pose') == attempt['sensing'].get('estimated_pose'), 'Estimated pose differs from observation')
            if row['success']:
                require(row['failure_stage'] == 'SUCCESS' and row['lift_success'] and row['place_success'], 'Wrong success stage')
                require(row['min_hold_height_m'] > row['episode_initial_height_m'] + .08, 'Insufficient lift')
                require(row['bilateral_contact_fraction'] >= .95, 'No stable bilateral hold')
                require(row['released'] and row['place_table_contact'] and row['place_distance_m'] < .055
                        and row['place_linear_speed_m_s'] < .02, 'Invalid place')
                require(scene_safe(row['scene_metrics']), 'Neighbor/collision gate failed')
            else:
                require(row['failure_stage'] != 'SUCCESS', 'Failure incorrectly marked SUCCESS')
        for obj in TARGETS:
            obj_rows = [r for r in rows if r['object_id'] == obj]
            require(summary['per_object'][obj]['trials'] == len(obj_rows)
                    and summary['per_object'][obj]['successes'] == sum(r['success'] for r in obj_rows), 'Object statistics mismatch')
        np.testing.assert_allclose(summary['success_rate_95pct_interval'], wilson_interval(summary['successes'], count), atol=1e-12)
        require(summary['success_rate'] == summary['successes'] / count, 'Wrong success rate')
        for metric in ('planning_time_s', 'execution_time_s', 'total_time_s'):
            require(math.isclose(summary['mean_' + metric], mean(r[metric] for r in rows), abs_tol=1e-10), 'Wrong timing summary')
        groups[name] = rows
        result[name] = {k: summary[k] for k in ('trials', 'successes', 'success_rate', 'success_rate_95pct_interval',
                        'failures', 'per_object', 'mean_planning_time_s', 'mean_total_time_s')}
        result[name]['mean_observed_frames'] = mean(r['observed_frames'] for r in rows)
        result[name]['failure_trials'] = [r['trial_id'] for r in rows if not r['success']]
        print(f"{name}: {summary['successes']}/{count} {summary['failures']}")
    pairs = {}
    for scene in ('clutter', 'dense'):
        before, after = groups['baseline_' + scene], groups['local_' + scene]
        for a, b in zip(before, after):
            require(a['object_id'] == b['object_id'], 'Object pairing mismatch')
            require(a['scene_metrics']['initial_scene'] == b['scene_metrics']['initial_scene'], 'Initial scene pairing mismatch')
            require(a.get('estimated_pose') == b.get('estimated_pose'), 'Observation pairing mismatch')
            require(a['candidate_count'] <= b['candidate_count'] <= a['candidate_count'] + 16, 'Expanded candidate budget exceeded')
        recovered = [a['trial_id'] for a, b in zip(before, after) if not a['success'] and b['success']]
        regressed = [a['trial_id'] for a, b in zip(before, after) if a['success'] and not b['success']]
        n = len(recovered) + len(regressed)
        p = min(1., 2 * sum(math.comb(n, k) for k in range(min(len(recovered), len(regressed)) + 1)) / 2**n) if n else 1.
        pairs[scene] = {'recovered_trials': recovered, 'regressed_trials': regressed, 'exact_mcnemar_p': p}
        print(f'{scene}: recovered {len(recovered)}, regressed {len(regressed)}, paired p={p:.4f}')
    comparison = {'source_sha256': expected_hash, 'seed': seed, 'cases': result, 'paired': pairs,
                  'episodes': sum(len(r) for r in groups.values()), 'provenance': provenance}
    (folder / 'comparison.json').write_text(json.dumps(comparison, indent=2) + '\n', encoding='utf-8')
    print(f"Verified {comparison['episodes']} physical episodes, exact scene/sensor pairing and unchanged gates")
    return comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, default=ROOT / 'docs/validation/v2.1.0')
    args = parser.parse_args()
    audit(args.folder)


if __name__ == '__main__':
    main()
