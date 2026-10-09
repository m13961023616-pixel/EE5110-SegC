"""Search correctness, deterministic bounds and real blocked-route transport."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from robot_manipulation.search import rrt_connect
from robot_manipulation.config import Config
from robot_manipulation.control import Controller
from robot_manipulation.planning import Planner
from robot_manipulation.obstacle_planning import ObstaclePlanner
from robot_manipulation.pipeline import trial
from robot_manipulation.perception import observe
from robot_manipulation.grasp import generate_candidates
from challenge_main import ChallengeEnvironment


class ObstacleChecks(unittest.TestCase):
    def test_obstacle_preview_keeps_live_state_unchanged(self):
        env = ChallengeEnvironment(Config(place_xy=(.48, .30)), object_names=['foam_brick'],
                                   obstacles=[{'center': [.485, .145, .11], 'half_size': [.12, .008, .11]}])
        try:
            env.reset(np.random.default_rng(1), fixed=True)
            candidate = generate_candidates(observe(env), env.config)[0]
            saved = (env.data.qpos.copy(), env.data.qvel.copy(), env.data.ctrl.copy(), env.data.time)
            planner = ObstaclePlanner(env, seed=42)
            pre = planner.plan(candidate.pregrasp)
            approach = planner.plan(candidate.pose, True, start_q=pre.joints[-1])
            planner.preview_task(candidate, approach, 'place')
            for actual, original in zip((env.data.qpos, env.data.qvel, env.data.ctrl), saved[:3]):
                np.testing.assert_array_equal(actual, original)
            self.assertEqual(env.data.time, saved[3])
        finally:
            env.close()

    def test_bidirectional_search_routes_around_blocked_edge(self):
        def free(a, b):
            points = np.linspace(a, b, 201)
            return not np.any((abs(points[:, 0]) < .2) & (abs(points[:, 1]) < .65))
        start, goal = np.array([-.8, 0]), np.array([.8, 0])
        limits = np.array([[-1, 1], [-1, 1]])
        path, stats = rrt_connect(start, goal, limits, free, np.random.default_rng(42))
        again, _ = rrt_connect(start, goal, limits, free, np.random.default_rng(42))
        self.assertIsNotNone(path)
        np.testing.assert_allclose(path[0], start)
        np.testing.assert_allclose(path[-1], goal)
        np.testing.assert_allclose(path, again)
        self.assertTrue(all(free(a, b) for a, b in zip(path[:-1], path[1:])))
        self.assertTrue(all(np.all((p >= limits[:, 0]) & (p <= limits[:, 1])) for p in path))
        self.assertLessEqual(stats['iterations'], 180)

    def test_impossible_search_is_bounded(self):
        path, stats = rrt_connect(np.array([0., 0.]), np.array([1., 1.]),
                                  np.array([[0, 1], [0, 1]]),
                                  lambda a, b: np.array_equal(a, b), np.random.default_rng(1), max_iterations=7)
        self.assertIsNone(path)
        self.assertEqual(stats['iterations'], 7)

    def test_physical_barrier_blocks_direct_and_allows_checked_detour(self):
        config = Config(spawn_y=(-.10, .06), place_xy=(.48, .30))
        wall = [{'center': [.485, .145, .11], 'half_size': [.12, .008, .11]}]
        env = ChallengeEnvironment(config, object_names=['foam_brick'], obstacles=wall)
        try:
            direct = Planner(env)
            original = trial(env, direct, Controller(env, direct), np.random.default_rng(1), 1,
                             fixed=True, object_id='foam_brick', task='place')
            self.assertFalse(original['success'])
            planner = ObstaclePlanner(env, seed=42)
            result = trial(env, planner, Controller(env, planner), np.random.default_rng(1), 2,
                           fixed=True, object_id='foam_brick', task='place')
            np.testing.assert_allclose(original['spawn_pose'], result['spawn_pose'])
            self.assertTrue(result['success'], result)
            self.assertTrue(result['released'] and result['place_table_contact'])
            self.assertEqual(env.barrier_contact_steps, 0)
            self.assertLessEqual(result['peak_gripper_force_n'], 40 + 1e-6)
            self.assertTrue(any(e['method'] == 'clearance_route' for e in planner.stats))
        finally:
            env.close()


if __name__ == '__main__':
    unittest.main()
