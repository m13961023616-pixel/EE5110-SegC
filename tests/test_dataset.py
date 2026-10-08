"""Meaningful multi-object scene, geometry and task integration checks."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
import numpy as np
from robot_manipulation.config import Config
from robot_manipulation.environment import Environment
from robot_manipulation.planning import Planner
from robot_manipulation.control import Controller
from robot_manipulation.pipeline import trial
from robot_manipulation.evaluation import verify_place, wilson_interval
from robot_manipulation.dataset import YCB_OBJECTS
from robot_manipulation.grasp import generate
from robot_manipulation.perception import observe


class DatasetChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = Environment(Config(), object_names=YCB_OBJECTS)

    def test_object_switch_disables_previous_collision_geometry(self):
        e = self.env
        e.reset(np.random.default_rng(7), fixed=True, object_id='lemon')
        previous = e.object_geoms.copy()
        e.reset(np.random.default_rng(7), fixed=True, object_id='foam_brick')
        self.assertTrue(all(e.model.geom_contype[g] == 0 for g in previous))
        self.assertTrue(all(e.model.geom_contype[g] != 0 for g in e.object_geoms))

    def test_untransported_object_is_not_successful_place(self):
        e = self.env
        e.reset(np.random.default_rng(7), fixed=True, object_id='foam_brick')
        self.assertFalse(verify_place(e)['place_success'])

    def test_real_mesh_pick_place_requires_physics_and_release(self):
        e = self.env
        p = Planner(e)
        result = trial(e, p, Controller(e, p), np.random.default_rng(42), 1,
                       fixed=True, object_id='foam_brick', task='place')
        self.assertTrue(result['success'], result)
        self.assertTrue(result['lift_success'])
        self.assertTrue(result['released'])
        self.assertTrue(result['place_table_contact'])

    def test_uncertainty_interval_includes_boundary(self):
        lo, hi = wilson_interval(0, 10)
        self.assertEqual(lo, 0.)
        self.assertGreater(hi, .2)

    def test_full_task_preview_does_not_move_real_state(self):
        e = self.env
        e.reset(np.random.default_rng(42), fixed=True, object_id='foam_brick')
        p = Planner(e)
        candidate = generate(observe(e), e.config)
        before = (e.data.qpos.copy(), e.data.qvel.copy(), e.data.ctrl.copy(), e.data.time)
        pre = p.plan(candidate.pregrasp)
        approach = p.plan(candidate.pose, True, start_q=pre.joints[-1])
        p.preview_task(candidate, approach, 'place')
        for original, current in zip(before[:3], (e.data.qpos, e.data.qvel, e.data.ctrl)):
            np.testing.assert_array_equal(original, current)
        self.assertEqual(before[3], e.data.time)

    def test_all_six_fixed_objects_place_with_bounded_grip_force(self):
        e = self.env
        p = Planner(e)
        for name in YCB_OBJECTS:
            with self.subTest(object=name):
                r = trial(e, p, Controller(e, p), np.random.default_rng(42), 1,
                          fixed=True, object_id=name, task='place')
                self.assertTrue(r['success'], r)
                self.assertLessEqual(r['peak_gripper_force_n'], e.config.gripper_force_limit + 1e-6)


if __name__ == '__main__':
    unittest.main(verbosity=2)
