from collections import Counter
from datetime import datetime
import json
from pathlib import Path
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
        self.summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
        return summary
