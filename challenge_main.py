"""Paired obstacle-transport experiments using unchanged physical task criteria."""
import argparse
from dataclasses import asdict
import hashlib
import json
import logging
from pathlib import Path
import platform
import mujoco
import numpy as np
from robot_manipulation.config import Config, ROOT
from robot_manipulation.dataset import YCB_OBJECTS
from robot_manipulation.environment import Environment
from robot_manipulation.control import Controller
from robot_manipulation.planning import Planner
from robot_manipulation.obstacle_planning import ObstaclePlanner
from robot_manipulation.robust_obstacles import RobustObstaclePlanner, symmetric_candidates
from robot_manipulation.grasp import generate_candidates
from robot_manipulation.pipeline import trial
from robot_manipulation.evaluation import Logger


class ChallengeEnvironment(Environment):
    """Record physical object/barrier penetration, including between waypoints."""
    def __init__(self, *args, **kwargs):
        self.barrier_contact_steps = 0
        self.max_barrier_penetration = 0.
        super().__init__(*args, **kwargs)
        self.barrier_geoms = {self.model.geom(f'obstacle_{i}').id for i in range(len(self.obstacles))}

    def reset(self, *args, **kwargs):
        self.barrier_contact_steps = 0
        self.max_barrier_penetration = 0.
        return super().reset(*args, **kwargs)

    def step(self):
        super().step()
        touched = False
        for contact in self.data.contact[:self.data.ncon]:
            if ((contact.geom1 in self.object_geoms and contact.geom2 in self.barrier_geoms) or
                (contact.geom2 in self.object_geoms and contact.geom1 in self.barrier_geoms)):
                self.max_barrier_penetration = max(self.max_barrier_penetration, -float(contact.dist))
                touched |= contact.dist < -.001
        self.barrier_contact_steps += int(touched)


def source_hash():
    digest = hashlib.sha256()
    for path in [ROOT / 'main.py', ROOT / 'challenge_main.py', *sorted((ROOT / 'robot_manipulation').glob('*.py'))]:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes().replace(b'\r\n', b'\n'))
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--planner', choices=['direct', 'rrt', 'clearance_rrt', 'robust'], default='robust')
    parser.add_argument('--scene', choices=['clear', 'barrier'], default='barrier')
    parser.add_argument('--height', type=float, default=.22, help='Barrier top above table, metres')
    parser.add_argument('--trials', type=int, default=6)
    parser.add_argument('--seed', type=int, default=20261201)
    parser.add_argument('--object', choices=YCB_OBJECTS)
    parser.add_argument('--fixed', action='store_true')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--fast', action='store_true')
    parser.add_argument('--require-all-success', action='store_true')
    parser.add_argument('--video', type=Path)
    parser.add_argument('--snapshot', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/challenge')
    args = parser.parse_args()
    if args.trials < 1 or not .12 <= args.height <= .30:
        parser.error('Positive trials and barrier height in [0.12, 0.30] required')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    config = Config(spawn_y=(-.10, .06), place_xy=(.48, .30), output_dir=args.output)
    obstacles = [] if args.scene == 'clear' else [
        {'center': [.485, .145, args.height / 2], 'half_size': [.12, .008, args.height / 2]}]
    roster = [args.object] if args.object else list(YCB_OBJECTS)
    rng = np.random.default_rng(args.seed)
    scenes = []
    while len(scenes) < args.trials:
        scenes.extend(str(x) for x in rng.permutation(roster))
    metadata = {'code_version': '2.0.0', 'scope': 'known_pose_single_object_static_barrier',
                'source_sha256': source_hash(), 'python': platform.python_version(),
                'mujoco': mujoco.__version__, 'numpy': np.__version__,
                'seed': args.seed, 'sampling': 'paired_balanced_scene_seeds',
                'planner': args.planner, 'scene': args.scene, 'obstacles': obstacles,
                'robot_model_commit': json.loads((ROOT / 'assets/panda.lock.json').read_text())['commit'],
                'dataset_commit': json.loads((ROOT / 'assets/ycb.lock.json').read_text())['commit'],
                'object_pool': roster, 'task': 'place', 'randomize': not args.fixed,
                'config': {k: str(v) if isinstance(v, Path) else v for k, v in asdict(config).items()}}
    logger = Logger(args.output, metadata)
    env = ChallengeEnvironment(config, gui=not args.headless, realtime=not args.fast,
                               object_names=roster, obstacles=obstacles)
    env.model.site_pos[env.model.site('place_target').id, :2] = config.place_xy
    if args.video:
        from robot_manipulation.video import Recorder
        env.recorder = Recorder(env, args.video)
        env.recorder.title = 'EE5110 | Obstacle-aware physical pick-and-place'
    interrupted = False
    try:
        for index, object_id in enumerate(scenes[:args.trials], 1):
            scene_seed, planner_seed = args.seed + 1000 + index, args.seed + 100000 + index
            planner = (Planner(env) if args.planner == 'direct' else
                       RobustObstaclePlanner(env, seed=planner_seed) if args.planner == 'robust' else
                       ObstaclePlanner(env, mode=args.planner, seed=planner_seed))
            result = trial(env, planner, Controller(env, planner), np.random.default_rng(scene_seed),
                           index, fixed=args.fixed, object_id=object_id, task='place',
                           candidate_generator=symmetric_candidates if args.planner == 'robust' else generate_candidates)
            result.update(scene_seed=scene_seed, planner_seed=planner_seed,
                          barrier_contact_steps=env.barrier_contact_steps,
                          max_barrier_penetration_m=env.max_barrier_penetration,
                          search_events=getattr(planner, 'stats', []))
            if result['success'] and env.barrier_contact_steps:
                result.update(success=False, failure_stage='COLLISION_FAIL',
                              reason='Physical object/barrier penetration exceeded 1 mm')
            logger.append(result)
        if args.snapshot:
            from robot_manipulation.visualization import save_snapshot
            save_snapshot(env, logger.path.with_suffix('.png'))
    except KeyboardInterrupt:
        interrupted = True
    finally:
        env.close()
        summary = logger.finish()
        print(f"{args.scene}/{args.planner}: {summary['successes']}/{summary['trials']}")
        print('Summary:', logger.summary_path)
    return 130 if interrupted else int(args.require_all_success and summary['successes'] != args.trials)


if __name__ == '__main__':
    raise SystemExit(main())
