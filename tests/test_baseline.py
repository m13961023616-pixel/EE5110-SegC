"""Regression checks for failure rejection, oracle reset and physical verification."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mujoco
import numpy as np
from robot_manipulation.config import Config
from robot_manipulation.environment import Environment
from robot_manipulation.planning import Planner, StageFailure
from robot_manipulation.evaluation import verify_lift


class BaselineChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = Environment(Config())
        cls.planner = Planner(cls.env)

    @classmethod
    def tearDownClass(cls):
        cls.env.close()

    def setUp(self):
        self.env.reset(np.random.default_rng(17))

    def test_seeded_reset_restores_object_and_robot(self):
        expected = self.env.object_pose()
        self.env.data.qpos[self.env.arm_qpos] += .1
        self.env.reset(np.random.default_rng(17))
        np.testing.assert_allclose(self.env.object_pose(), expected, atol=1e-10)

    def test_unreachable_pose_is_rejected(self):
        self.planner.prepare()
        target = self.env.site_pose()
        target[:3, 3] = [4., 0., 4.]
        with self.assertRaises(StageFailure) as caught:
            self.planner.ik(target, self.env.data.qpos[self.env.arm_qpos])
        self.assertEqual(caught.exception.stage, 'IK_FAIL')

    def test_object_robot_intersection_is_detected(self):
        env = self.env
        self.planner.prepare()
        data = self.planner.scratch
        # Put the cube inside the palm on scratch data, never teleport during execution.
        data.qpos[env.object_qpos:env.object_qpos + 3] = env.data.xpos[env.model.body('hand').id] + [0, 0, -.015]
        mujoco.mj_forward(env.model, data)
        self.assertIsNotNone(self.planner.forbidden_contacts(data))

    def test_cube_resting_on_table_does_not_count_as_lift(self):
        result = verify_lift(self.env, self.env.object_pose()[2, 3])
        self.assertFalse(result['lift_success'])
        self.assertEqual(result['bilateral_contact_fraction'], 0.)


if __name__ == '__main__':
    unittest.main(verbosity=2)
