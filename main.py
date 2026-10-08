"""PyCharm entry point for the YCB robotic grasping simulation baseline."""
import argparse
from dataclasses import asdict
import logging
from pathlib import Path
import platform
import json
import mujoco
import numpy as np
from robot_manipulation.config import Config, ROOT
from robot_manipulation.environment import Environment
from robot_manipulation.dataset import YCB_OBJECTS
from robot_manipulation.planning import Planner
from robot_manipulation.control import Controller
from robot_manipulation.evaluation import Logger
from robot_manipulation.pipeline import trial

LOG = logging.getLogger('baseline')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless', action='store_true', help='Run without a GUI')
    parser.add_argument('--trials', type=int, default=1)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--dataset', choices=['cube', 'ycb'], default='ycb')
    parser.add_argument('--object', choices=YCB_OBJECTS, help='Use one YCB object instead of random selection')
    parser.add_argument('--task', choices=['pick', 'place'], default='pick')
    parser.add_argument('--fixed', action='store_true', help='Fixed x/y/yaw for debugging')
    parser.add_argument('--randomize', action='store_true', help='Randomize cube too; YCB is randomized by default')
    parser.add_argument('--require-all-success', action='store_true', help='Return failure if any evaluated trial fails')
    parser.add_argument('--fast', action='store_true', help='Disable real-time pacing in GUI')
    parser.add_argument('--snapshot', action='store_true', help='Save final scene PNG (requires OpenGL)')
    parser.add_argument('--video', type=Path, help='Optional MP4; install requirements-video.txt')
    parser.add_argument('--keep-open', action='store_true', help='Keep GUI open after trials for inspection')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs')
    args = parser.parse_args()
    if args.trials < 1:
        parser.error('--trials must be positive')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    config = Config(output_dir=args.output)
    roster = ['primitive_cube'] if args.dataset == 'cube' else ([args.object] if args.object else list(YCB_OBJECTS))
    randomized = not args.fixed and (args.dataset == 'ycb' or args.randomize)
    metadata = {'python': platform.python_version(), 'mujoco': mujoco.__version__,
                'numpy': np.__version__, 'seed': args.seed, 'randomize': randomized,
                'scope': 'YCB_known_object_baseline' if args.dataset == 'ycb' else 'primitive_cube_regression',
                'code_version': '1.0.0',
                'dataset': args.dataset, 'object_pool': roster, 'task': args.task,
                'config': {k: str(v) if isinstance(v, Path) else v for k, v in asdict(config).items()}}
    manifest = ROOT / 'assets/panda/manifest.json'
    if manifest.exists():
        metadata['robot_model_commit'] = json.loads(manifest.read_text())['commit']
    if args.dataset == 'ycb':
        metadata['dataset_commit'] = json.loads((ROOT / 'assets/ycb.lock.json').read_text())['commit']
    logger = Logger(args.output, metadata)
    env = Environment(config, gui=not args.headless, realtime=not args.fast, object_names=roster)
    if args.video:
        from robot_manipulation.video import Recorder
        env.recorder = Recorder(env, args.video)
    planner = Planner(env)
    controller = Controller(env, planner)
    rng = np.random.default_rng(args.seed)
    interrupted = False
    try:
        for trial_id in range(1, args.trials + 1):
            object_id = roster[int(rng.integers(len(roster)))] if len(roster) > 1 else roster[0]
            logger.append(trial(env, planner, controller, rng, trial_id, fixed=not randomized,
                                object_id=object_id, task=args.task))
        if args.snapshot:
            from robot_manipulation.visualization import save_snapshot
            try:
                image_path = logger.path.with_suffix('.png')
                save_snapshot(env, image_path)
                LOG.info('Scene snapshot: %s', image_path)
            except Exception as exc:
                LOG.warning('Optional snapshot failed: %s', exc)
        if args.keep_open and env.viewer:
            LOG.info('Trials finished. Close the simulation window to exit.')
            while env.viewer.is_running():
                env.step()
    except KeyboardInterrupt:
        interrupted = True
        LOG.info('Run interrupted; completed trial records preserved.')
    finally:
        env.close()
        summary = logger.finish()
        print(json.dumps(summary, indent=2))
        print('Trial log:', logger.path)
        print('Summary:', logger.summary_path)
    # Evaluation measures failures; they are valid outcomes, not process crashes.
    return 130 if interrupted else (1 if args.require_all_success and summary['successes'] != args.trials else 0)


if __name__ == '__main__':
    raise SystemExit(main())
