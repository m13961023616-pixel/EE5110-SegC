"""Measured geometry, failure gates, state isolation and real contact execution."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from robot_manipulation.depth_sensing import DepthConfig, DepthObserver, estimate_box_pose, transparent_appearance
from robot_manipulation.config import Config
from robot_manipulation.environment import Environment
from robot_manipulation.planning import Planner, StageFailure
from robot_manipulation.pipeline import trial
from robot_manipulation.control import Controller


class SensingChecks(unittest.TestCase):
    def test_pose_fit_only_uses_points_and_template(self):
        vertices=np.array([[x,y,z] for x in (-.04,.04) for y in (-.025,.025) for z in (-.02,.02)])
        yaw=.43; c,s=np.cos(yaw),np.sin(yaw);r=np.array([[c,-s,0],[s,c,0],[0,0,1]])
        pts=np.array([[x,y,.02] for x in np.linspace(-.04,.04,30) for y in np.linspace(-.025,.025,25)])@r.T+[.48,.02,.02]
        fit=estimate_box_pose(pts,'foam_brick',vertices)
        np.testing.assert_allclose(fit.pose[:3,3],[.48,.02,.02],atol=.001)
        self.assertLess(abs(fit.pose[0,0]-c),.01)

    def test_zero_returns_fail_without_oracle_fallback(self):
        with self.assertRaises(StageFailure):estimate_box_pose(np.zeros((40,3)),'foam_brick',np.zeros((8,3)))
        with self.assertRaises(ValueError):DepthConfig(dropout=1.01)

    def test_sensing_preserves_physics_and_real_state(self):
        env=Environment(Config(),object_names=['pudding_box'])
        try:
            env.reset(np.random.default_rng(1045))
            q=env.data.qpos.copy();v=env.data.qvel.copy();ctrl=env.data.ctrl.copy();t=env.data.time
            mass=env.model.body_mass.copy();friction=env.model.geom_friction.copy()
            transparent_appearance(env)
            observer=DepthObserver(DepthConfig(),100045)
            observer(env)
            for before,after in [(q,env.data.qpos),(v,env.data.qvel),(ctrl,env.data.ctrl),(mass,env.model.body_mass),(friction,env.model.geom_friction)]:
                np.testing.assert_array_equal(before,after)
            self.assertEqual(t,env.data.time)
        finally:env.close()

    def test_estimated_pose_drives_actual_release(self):
        env=Environment(Config(),object_names=['pudding_box']);planner=Planner(env)
        try:
            obs=DepthObserver(DepthConfig(),100045)
            result=trial(env,planner,Controller(env,planner),np.random.default_rng(1045),1,
                         object_id='pudding_box',task='place',observer=obs)
            self.assertTrue(result['success'],result)
            self.assertTrue(result['released'] and result['place_table_contact'])
            self.assertLessEqual(result['peak_gripper_force_n'],40+1e-6)
        finally:env.close()


if __name__=='__main__':unittest.main()
