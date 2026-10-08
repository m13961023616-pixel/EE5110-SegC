"""PyCharm entry point: run directly for one visual fixed-cube trial."""
import argparse
from dataclasses import asdict
import logging
from pathlib import Path
import platform
import time
import json
import mujoco
import numpy as np
from robot_manipulation.config import Config, ROOT
from robot_manipulation.environment import Environment
from robot_manipulation.perception import observe
from robot_manipulation.grasp import generate
from robot_manipulation.planning import Planner, StageFailure
from robot_manipulation.control import Controller
from robot_manipulation.evaluation import Logger, verify_lift

LOG = logging.getLogger('baseline')


def trial(env, planner, controller, rng, trial_id, fixed):
    started = time.perf_counter()
    result = {'trial_id': trial_id, 'object_id': 'primitive_cube', 'success': False,
              'failure_stage': 'SPAWN_FAIL', 'planning_time_s': 0., 'execution_time_s': 0.}
    stage = 'SPAWN_FAIL'
    try:
        env.reset(rng, fixed)
        state = observe(env)
        result['spawn_pose'] = state.pose.tolist()
        stage = 'GRASP_GENERATION_FAIL'
        candidate = generate(state, env.config)
        result['grasp_pose'] = candidate.pose.tolist()
        controller.gripper(.08)
        for name, target, cartesian, attached in [
            ('PRE_GRASP', candidate.pregrasp, False, False),
            ('APPROACH', candidate.pose, True, False),
            ('LIFT', candidate.lift, True, True),
        ]:
            LOG.info('Trial %d: %s', trial_id, name)
            if name == 'LIFT':
                controller.gripper(0)
                result['grasp_contacts'] = len(env.finger_contacts())
                if result['grasp_contacts'] < 2:
                    raise StageFailure('GRASP_FAIL', 'Both fingers did not contact the object')
            stage = 'PLANNING_FAIL'
            tick = time.perf_counter()
            trajectory = planner.plan(target, cartesian, allow_finger_object=attached, attached=attached)
            result['planning_time_s'] += time.perf_counter() - tick
            stage = 'EXECUTION_FAIL'
            tick = time.perf_counter()
            controller.execute(trajectory, allow_finger_object=attached)
            result['execution_time_s'] += time.perf_counter() - tick
        stage = 'SLIP_FAIL'
        result.update(verify_lift(env, state.pose[2, 3]))
        result['success'] = result['lift_success'] and result['bilateral_contact_fraction'] >= .95
        result['failure_stage'] = 'SUCCESS' if result['success'] else 'SLIP_FAIL'
    except StageFailure as exc:
        result['failure_stage'] = exc.stage
        result['reason'] = str(exc)
    except (RuntimeError, ValueError, np.linalg.LinAlgError) as exc:
        result['failure_stage'] = stage
        result['reason'] = f'{type(exc).__name__}: {exc}'
    result['total_time_s'] = time.perf_counter() - started
    LOG.info('Trial %d: %s %s', trial_id, result['failure_stage'], result.get('reason', ''))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless', action='store_true', help='Run without a GUI')
    parser.add_argument('--trials', type=int, default=1)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--randomize', action='store_true', help='Random x/y/yaw; otherwise fixed cube')
    parser.add_argument('--fast', action='store_true', help='Disable real-time pacing in GUI')
    parser.add_argument('--snapshot', action='store_true', help='Save final scene PNG (requires OpenGL)')
    parser.add_argument('--keep-open', action='store_true', help='Keep GUI open after trials for inspection')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs')
    args = parser.parse_args()
    if args.trials < 1:
        parser.error('--trials must be positive')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    config = Config(output_dir=args.output)
    metadata = {'python': platform.python_version(), 'mujoco': mujoco.__version__,
                'numpy': np.__version__, 'seed': args.seed, 'randomize': args.randomize,
                'scope': 'primitive_cube_development_baseline',
                'config': {k: str(v) if isinstance(v, Path) else v for k, v in asdict(config).items()}}
    manifest = ROOT / 'assets/panda/manifest.json'
    if manifest.exists():
        metadata['robot_model_commit'] = json.loads(manifest.read_text())['commit']
    logger = Logger(args.output, metadata)
    env = Environment(config, gui=not args.headless, realtime=not args.fast)
    planner = Planner(env)
    controller = Controller(env, planner)
    rng = np.random.default_rng(args.seed)
    interrupted = False
    try:
        for trial_id in range(1, args.trials + 1):
            logger.append(trial(env, planner, controller, rng, trial_id, fixed=not args.randomize))
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
    return 130 if interrupted else (0 if summary['successes'] == args.trials else 1)


if __name__ == '__main__':
    raise SystemExit(main())
