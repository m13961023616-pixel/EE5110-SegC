"""Runnable studies for every bounded exploratory direction in the CA brief."""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import platform
import time
import mujoco
import numpy as np
from exploration.protocol import CASES, GATES
from exploration.provenance import source_hash
from exploration.runner import make_environment, run_case_episode
from robot_manipulation.config import ROOT
from robot_manipulation.evaluation import wilson_interval


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=CASES, default='novel_points')
    parser.add_argument('--trials', type=int, default=3)
    parser.add_argument('--seed', type=int, default=43)
    parser.add_argument('--output', type=Path, default=ROOT/'outputs/exploration')
    parser.add_argument('--headless', action='store_true', help='Batch-compatible flag; no GUI is started by default')
    parser.add_argument('--video', type=Path)
    parser.add_argument('--snapshot', action='store_true')
    parser.add_argument('--require-all-success', action='store_true')
    args = parser.parse_args()
    if args.trials < 1 or (args.video and args.trials != 1):
        parser.error('Positive trials required; one scene per recorded video')
    args.output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    rows_path = args.output/f'trials_{stamp}.jsonl'
    case = CASES[args.case]; frozen = source_hash(); rows = []
    for index in range(1, args.trials+1):
        if source_hash() != frozen:
            raise RuntimeError('Research engine changed during evaluation')
        asset_seed = args.seed+300000+index
        env = make_environment(case, asset_seed)
        if args.snapshot:
            from robot_manipulation.visualization import save_snapshot
            def capture_event(stage):
                save_snapshot(env, args.output/f'{args.case}_{index}_{stage}.png')
            env.capture_event = capture_event
        if args.video:
            from robot_manipulation.video import Recorder
            # Visualization-only camera/illumination, shared across all recorded studies.
            env.model.vis.headlight.ambient[:] = .35
            env.recorder = Recorder(env, args.video)
            env.recorder.title = 'EE5110 explorations | '+args.case
        try:
            row = run_case_episode(env, case, args.seed, index)
            row.update(case=args.case, source_sha256=frozen)
            rows.append(row)
            with rows_path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(row)+'\n')
            print(f"{args.case} {index}/{args.trials}: {row['failure_stage']}", flush=True)
            if args.snapshot:
                from robot_manipulation.visualization import save_snapshot
                save_snapshot(env, rows_path.with_suffix('.png'))
        finally:
            env.close()
    if source_hash() != frozen:
        raise RuntimeError('Research engine changed before experiment completion')
    successes = sum(r['success'] for r in rows)
    summary = {'version':'3.0.0', 'case':args.case, 'case_definition':case, 'seed':args.seed,
               'source_sha256':frozen, 'trials':len(rows), 'successes':successes,
               'first_successes':sum(r['first_attempt_success'] for r in rows),
               'success_rate_95pct_interval':wilson_interval(successes,len(rows)),
               'failures':dict(Counter(r['failure_stage'] for r in rows if not r['success'])),
               'mean_total_time_s':float(np.mean([r['total_time_s'] for r in rows])),
               'gates':GATES, 'python':platform.python_version(),'mujoco':mujoco.__version__,'numpy':np.__version__,
               'robot_model_commit':json.loads((ROOT/'assets/panda.lock.json').read_text())['commit'],
               'dataset_commit':json.loads((ROOT/'assets/ycb.lock.json').read_text())['commit']}
    (args.output/f'summary_{stamp}.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(f'{successes}/{len(rows)}; {rows_path}')
    return int(args.require_all_success and successes != len(rows))


if __name__ == '__main__':
    raise SystemExit(main())
