"""Bounded confidence-based observations and contact-based execution."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from robot_manipulation.active_sensing import ActiveObserver, ActiveConfig, confidence
from robot_manipulation.depth_sensing import estimate_box_pose
from robot_manipulation.environment import Environment
from robot_manipulation.config import Config
from robot_manipulation.planning import Planner, StageFailure
from robot_manipulation.control import Controller
from robot_manipulation.pipeline import trial


class ActiveChecks(unittest.TestCase):
    def test_early_stop_preserves_live_state(self):
        e = Environment(Config(), object_names=['pudding_box'])
        try:
            e.reset(np.random.default_rng(1045)); before = e.data.qpos.copy()
            o = ActiveObserver(seed=100045); o(e)
            self.assertLess(o.metrics['used_frames'], 64)
            self.assertTrue(o.metrics['checks'][-1]['accepted'])
            np.testing.assert_array_equal(before, e.data.qpos)
        finally:e.close()

    def test_budget_exhaustion_has_no_pose_fallback(self):
        e = Environment(Config(), object_names=['foam_brick'])
        try:
            e.reset(np.random.default_rng(43));o=ActiveObserver(ActiveConfig(dropout=1.), seed=43)
            with self.assertRaises(StageFailure):o(e)
            self.assertEqual(o.metrics['used_frames'],64)
            self.assertNotIn('estimated_pose',o.metrics)
        finally:e.close()

    def test_stable_but_partial_footprint_is_rejected(self):
        vertices = np.array([[x,y,z] for x in (-.04,.04) for y in (-.025,.025) for z in (-.02,.02)])
        points=np.array([[x,y,.04] for x in np.linspace(.45,.48,30) for y in np.linspace(-.025,.025,25)])
        state=estimate_box_pose(points,'foam_brick',vertices)
        check=confidence(points,state,ActiveConfig(),state)
        self.assertFalse(check['accepted'])

    def test_active_estimate_drives_real_release(self):
        e=Environment(Config(),object_names=['pudding_box']);p=Planner(e)
        try:
            r=trial(e,p,Controller(e,p),np.random.default_rng(1045),1,object_id='pudding_box',task='place',observer=ActiveObserver(seed=100045))
            self.assertTrue(r['success'],r)
            self.assertTrue(r['released'] and r['place_table_contact'])
        finally:e.close()


if __name__=='__main__':unittest.main()
