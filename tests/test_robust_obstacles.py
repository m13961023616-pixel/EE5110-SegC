"""Physical regression for a blocked elbow, symmetry and live-state isolation."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from challenge_main import ChallengeEnvironment
from robot_manipulation.config import Config
from robot_manipulation.dataset import YCB_OBJECTS
from robot_manipulation.control import Controller
from robot_manipulation.obstacle_planning import ObstaclePlanner
from robot_manipulation.robust_obstacles import RobustObstaclePlanner, symmetric_candidates
from robot_manipulation.pipeline import trial
from robot_manipulation.perception import observe


def environment():
    return ChallengeEnvironment(Config(spawn_y=(-.10, .06), place_xy=(.48, .30)),
                                object_names=YCB_OBJECTS,
                                obstacles=[{'center': [.485, .145, .14], 'half_size': [.12, .008, .14]}])


class RobustChecks(unittest.TestCase):
    def test_equivalent_jaws_keep_pose_point_and_approach(self):
        env = environment()
        try:
            env.reset(np.random.default_rng(1), fixed=True, object_id='foam_brick')
            candidates = symmetric_candidates(observe(env), env.config)
            for a, b in zip(candidates[::2], candidates[1::2]):
                np.testing.assert_allclose(a.pose[:3, 3], b.pose[:3, 3])
                np.testing.assert_allclose(a.pose[:3, 2], b.pose[:3, 2])
                np.testing.assert_allclose(a.pose[:3, 1], -b.pose[:3, 1])
                self.assertEqual(a.width, b.width)
                self.assertAlmostEqual(np.linalg.det(b.pose[:3, :3]), 1)
        finally:
            env.close()

    def test_collision_filtered_ik_recovers_known_elbow_failure(self):
        env = environment()
        try:
            seed = 20262308
            original = ObstaclePlanner(env, seed=20361308)
            before = trial(env, original, Controller(env, original), np.random.default_rng(seed), 7,
                           object_id='foam_brick', task='place')
            self.assertFalse(before['success'])
            planner = RobustObstaclePlanner(env, seed=20361308)
            after = trial(env, planner, Controller(env, planner), np.random.default_rng(seed), 7,
                          object_id='foam_brick', task='place', candidate_generator=symmetric_candidates)
            np.testing.assert_allclose(before['spawn_pose'], after['spawn_pose'], rtol=0, atol=1e-10)
            self.assertTrue(after['success'], after)
            self.assertEqual(env.barrier_contact_steps, 0)
            self.assertLessEqual(after['peak_gripper_force_n'], 40 + 1e-6)
            self.assertTrue(any(s['method'] == 'ik_reseed' and s['success'] for s in planner.stats))
        finally:
            env.close()

    def test_robust_full_task_preview_preserves_live_state(self):
        env = environment()
        try:
            env.reset(np.random.default_rng(20262308), object_id='foam_brick')
            saved = [env.data.qpos.copy(), env.data.qvel.copy(), env.data.ctrl.copy(), env.data.time]
            planner = RobustObstaclePlanner(env, seed=20361308)
            candidate = symmetric_candidates(observe(env), env.config)[0]
            pre = planner.plan(candidate.pregrasp)
            approach = planner.plan(candidate.pose, True, start_q=pre.joints[-1])
            planner.preview_task(candidate, approach, 'place')
            for current, old in zip((env.data.qpos, env.data.qvel, env.data.ctrl), saved[:3]):
                np.testing.assert_array_equal(current, old)
            self.assertEqual(env.data.time, saved[3])
        finally:
            env.close()


if __name__ == '__main__':
    unittest.main()
