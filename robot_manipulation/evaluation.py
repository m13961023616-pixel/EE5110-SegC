from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import csv
import numpy as np


def verify_lift(env, initial_height):
    heights, contacts = [], []
    for _ in range(round(env.config.hold_seconds / env.config.timestep)):
        env.step()
        heights.append(float(env.object_pose()[2, 3]))
        contacts.append(len(env.finger_contacts()) == 2)
    return {
        'lift_success': bool(min(heights) > initial_height + env.config.success_height),
        'bilateral_contact_fraction': float(np.mean(contacts)),
        'initial_height_m': float(initial_height),
        'final_height_m': heights[-1],
        'min_hold_height_m': min(heights),
    }


def verify_place(env):
    """Check release, support contact, position and settled object motion."""
    env.step_for(1.0)
    pose = env.object_pose()
    distance = float(np.linalg.norm(pose[:2, 3] - env.config.place_xy))
    table_contact = any((c.geom1 in env.object_geoms and c.geom2 == env.table_geom) or
                        (c.geom2 in env.object_geoms and c.geom1 == env.table_geom)
                        for c in env.data.contact[:env.data.ncon] if c.dist < .001)
    dof = env.model.jnt_dofadr[env.model.body_jntadr[env.object_body]]
    speed = float(np.linalg.norm(env.data.qvel[dof:dof + 3]))
    released = len(env.finger_contacts()) == 0
    return {'place_success': bool(distance < env.config.place_tolerance and table_contact and speed < .02 and released),
            'place_distance_m': distance, 'place_table_contact': bool(table_contact),
            'place_linear_speed_m_s': speed, 'released': released, 'placed_pose': pose.tolist()}


def wilson_interval(successes, total):
    if not total:
        return [0., 1.]
    z = 1.96
    p = successes / total
    denominator = 1 + z*z / total
    center = (p + z*z / (2 * total)) / denominator
    radius = z * np.sqrt(p * (1-p) / total + z*z / (4 * total*total)) / denominator
    return [max(0., float(center - radius)), min(1., float(center + radius))]


class Logger:
    def __init__(self, output_dir, metadata):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        self.path = output_dir / f'trials_{stamp}.jsonl'
        self.summary_path = output_dir / f'summary_{stamp}.json'
        self.metadata = metadata
        self.records = []

    def append(self, result):
        self.records.append(result)
        with self.path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(result, ensure_ascii=False) + '\n')

    def finish(self):
        successes = sum(r['success'] for r in self.records)
        summary = dict(self.metadata, trials=len(self.records), successes=successes,
                       success_rate=successes / len(self.records) if self.records else None,
                       failures=dict(Counter(r['failure_stage'] for r in self.records if not r['success'])))
        summary['success_rate_95pct_interval'] = wilson_interval(successes, len(self.records))
        summary['per_object'] = {}
        for object_id in sorted({r['object_id'] for r in self.records}):
            rows = [r for r in self.records if r['object_id'] == object_id]
            count = sum(r['success'] for r in rows)
            summary['per_object'][object_id] = {'trials': len(rows), 'successes': count,
                                               'success_rate': count / len(rows),
                                               'lift_successes': sum(r.get('lift_success', False) for r in rows),
                                               'place_successes': sum(r.get('place_success', False) for r in rows),
                                               'failures': dict(Counter(r['failure_stage'] for r in rows if not r['success']))}
        for metric in ('planning_time_s', 'execution_time_s', 'total_time_s'):
            summary['mean_' + metric] = float(np.mean([r.get(metric, 0) for r in self.records])) if self.records else None
        csv_path = self.path.with_suffix('.csv')
        fields = ['trial_id', 'object_id', 'success', 'failure_stage', 'lift_success', 'place_success',
                  'candidate_count', 'planning_time_s', 'execution_time_s', 'total_time_s', 'reason']
        with csv_path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.records)
        self.summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
        return summary
