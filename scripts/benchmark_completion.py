"""Frozen, balanced candidate-strategy ablation in exactly paired scenes."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from clutter_main import source_hash

CASES = {
    'baseline_clutter': ('clutter', 'baseline', 60),
    'local_clutter': ('clutter', 'local', 60),
    'baseline_dense': ('dense', 'baseline', 30),
    'local_dense': ('dense', 'local', 30),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/completion_frozen')
    parser.add_argument('--seed', type=int, default=20261025)
    parser.add_argument('--resume', action='store_true', help='Reuse complete groups; never overwrite partial groups')
    parser.add_argument('--cases', nargs='+', choices=CASES, default=list(CASES))
    parser.add_argument('--workers', type=int, choices=(1, 2, 3, 4), default=1)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()) and not args.resume:
        parser.error('Use a new output directory; previous failures must not be overwritten')
    args.output.mkdir(parents=True, exist_ok=True)
    frozen = source_hash()
    protocol = {
        'version': '2.1.0', 'seed': args.seed, 'source_sha256': frozen,
        'design': 'paired_candidate_strategy_ablation', 'mode': 'active',
        'cases': {name: {'scene': scene, 'grasps': grasps, 'trials': count}
                  for name, (scene, grasps, count) in CASES.items()},
        'development_seed': 20261601,
        'success_gates': {'lift_m': .08, 'hold_s': 1., 'bilateral_fraction': .95,
                          'place_m': .055, 'speed_m_s': .02, 'force_n': 40.,
                          'neighbor_m': .02, 'target_penetration_m': .001, 'unsafe_contact_steps': 0},
        'completed': False,
    }
    protocol_path = args.output / 'protocol.json'
    if args.resume:
        existing = json.loads(protocol_path.read_text(encoding='utf-8'))
        for key in ('version', 'seed', 'source_sha256', 'cases', 'success_gates', 'mode'):
            if existing[key] != protocol[key]:
                raise ValueError(f'Cannot resume changed protocol: {key}')
    else:
        protocol_path.write_text(json.dumps(protocol, indent=2) + '\n', encoding='utf-8')

    def run_case(name):
        scene, grasps, count = CASES[name]
        if source_hash() != frozen:
            raise RuntimeError('Engine changed during the experiment')
        folder = args.output / name
        if folder.exists():
            summaries = list(folder.glob('summary_*.json'))
            if len(summaries) == 1:
                summary = json.loads(summaries[0].read_text(encoding='utf-8'))
                if summary['source_sha256'] == frozen and summary['trials'] == count:
                    print(f'Reusing complete group {name}; final audit verifies every row', flush=True)
                    return
            raise ValueError(f'Incomplete group {folder}; preserve it and use a new experiment directory')
        folder.mkdir()
        print(f'Starting {name}: {count} physical episodes', flush=True)
        with (folder / 'run.log').open('w', encoding='utf-8') as stream:
            subprocess.run([sys.executable, str(ROOT / 'clutter_main.py'), '--headless',
                            '--scene', scene, '--mode', 'active', '--grasps', grasps,
                            '--seed', str(args.seed), '--trials', str(count), '--output', str(folder)],
                           cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)
        if source_hash() != frozen:
            raise RuntimeError('Engine changed during a case; results are not frozen')
        summary = json.loads(next(folder.glob('summary_*.json')).read_text(encoding='utf-8'))
        print(f"{name}: {summary['successes']}/{count}; {summary['failures']}", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(run_case, args.cases))
    if not all(len(list((args.output / name).glob('summary_*.json'))) == 1 for name in CASES):
        print('Selected groups complete; remaining groups still required', flush=True)
        return
    protocol['completed'] = True
    protocol_path.write_text(json.dumps(protocol, indent=2) + '\n', encoding='utf-8')
    subprocess.run([sys.executable, str(ROOT / 'scripts/check_completion_evidence.py'),
                    '--folder', str(args.output)], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
