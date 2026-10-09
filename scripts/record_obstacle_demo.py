"""Record a fixed physical challenge from the placement side of the barrier.

Only the viewing camera differs from the benchmark; physics is unchanged.
"""
import json
from pathlib import Path
import sys
import mujoco
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from challenge_main import ChallengeEnvironment
from robot_manipulation.config import Config
from robot_manipulation.control import Controller
from robot_manipulation.obstacle_planning import ObstaclePlanner
from robot_manipulation.pipeline import trial
from robot_manipulation.video import Recorder
from robot_manipulation.visualization import save_snapshot


def main():
    env = ChallengeEnvironment(Config(spawn_y=(-.10, .06), place_xy=(.48, .30)),
                               object_names=['foam_brick'],
                               obstacles=[{'center': [.485, .145, .11], 'half_size': [.12, .008, .11]}])
    camera = env.model.camera('overview').id
    env.model.cam_pos[camera] = [1.3, 1.3, 1.1]
    x = np.array([-.707, .707, 0.]); x /= np.linalg.norm(x)
    y = np.array([-.35, -.35, .87]); y /= np.linalg.norm(y)
    mujoco.mju_mat2Quat(env.model.cam_quat[camera], np.column_stack((x, y, np.cross(x, y))).ravel())
    env.model.site_pos[env.model.site('place_target').id, :2] = env.config.place_xy
    output = ROOT / 'deliverables/obstacle_demo_v1.2.0.mp4'
    env.recorder = Recorder(env, output)
    env.recorder.title = 'EE5110 | Clearance + RRT obstacle transport'
    planner = ObstaclePlanner(env, seed=42)
    try:
        result = trial(env, planner, Controller(env, planner), np.random.default_rng(42), 1,
                       fixed=True, object_id='foam_brick', task='place')
        assert result['success'] and not env.barrier_contact_steps, result
        save_snapshot(env, ROOT / 'docs/images/obstacle_place_v1.2.0.png')
        folder = ROOT / 'outputs/obstacle_demo'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'recording_result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(output)
    finally:
        env.close()


if __name__ == '__main__':
    main()
