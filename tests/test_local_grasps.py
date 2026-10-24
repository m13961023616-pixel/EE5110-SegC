"""Recover a real blocked-palm scene without changing its physical gates."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from robot_manipulation.clutter import ClutterEnvironment, compound_obstacles
from robot_manipulation.config import Config
from robot_manipulation.active_sensing import ActiveObserver
from robot_manipulation.clutter_planning import ClutterPlanner
from robot_manipulation.control import Controller
from robot_manipulation.pipeline import trial
from robot_manipulation.local_grasps import local_candidates
from robot_manipulation.robust_obstacles import symmetric_candidates


class LocalGraspChecks(unittest.TestCase):
    def test_blocked_palm_recovered_by_checked_inclined_grasp(self):
        env = ClutterEnvironment(Config(spawn_x=(.43, .52), spawn_y=(-.105, -.065),
                                       place_xy=(.48, .30)), distractors=3, obstacles=compound_obstacles())
        try:
            results = []
            for generator in (symmetric_candidates, local_candidates):
                planner = ClutterPlanner(env, seed=20461609)
                result = trial(env, planner, Controller(env, planner), np.random.default_rng(20262609), 1,
                               object_id='foam_brick', task='place', candidate_generator=generator,
                               observer=ActiveObserver(seed=20361609, instance_mask=True))
                results.append(result)
            before, after = results
            self.assertFalse(before['success'])
            self.assertEqual(before['candidate_rejections'][0]['phase'], 'approach')
            np.testing.assert_array_equal(before['spawn_pose'], after['spawn_pose'])
            self.assertTrue(after['success'], after)
            self.assertGreaterEqual(after['selected_candidate'], before['candidate_count'])
            self.assertTrue(after['released'] and after['place_table_contact'])
            self.assertLessEqual(after['peak_gripper_force_n'], 40 + 1e-6)
            self.assertEqual(env.scene_metrics()['unsafe_contact_steps'], 0)
            self.assertLessEqual(env.scene_metrics()['distractor_max_displacement_m'], .02)
        finally:
            env.close()

    def test_candidates_preserve_prefix_budget_and_width(self):
        from robot_manipulation.perception import ObjectState
        from itertools import product
        vertices = np.array(list(product((-.026, .026), (-.039, .039), (-.026, .026))))
        pose = np.eye(4); pose[:3, 3] = [.48, -.08, .026]
        state = ObjectState('test_box', pose, np.ptp(vertices, axis=0), vertices)
        baseline = symmetric_candidates(state, Config())
        candidates = local_candidates(state, Config())
        self.assertGreater(len(candidates), len(baseline))
        self.assertLessEqual(len(candidates), len(baseline) + 16)
        for actual, expected in zip(candidates, baseline):
            np.testing.assert_array_equal(actual.pose, expected.pose)
        for candidate in candidates:
            self.assertLessEqual(candidate.width, .080)
            self.assertAlmostEqual(np.linalg.det(candidate.pose[:3, :3]), 1.)


if __name__ == '__main__':
    unittest.main()
