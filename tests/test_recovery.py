from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from robot_manipulation.environment import Environment
from robot_manipulation.config import Config
from robot_manipulation.planning import Planner, StageFailure
from robot_manipulation.feedback import FeedbackController
from robot_manipulation.active_sensing import ActiveObserver
from robot_manipulation.recovery import episode


class RecoveryChecks(unittest.TestCase):
    def test_perception_retry_preserves_scene_and_uses_one_reset(self):
        env=Environment(Config(),object_names=['pudding_box']);p=Planner(env);c=FeedbackController(env,p)
        reset=env.reset;calls=[]
        def counted_reset(*args,**kwargs):
            calls.append(1);return reset(*args,**kwargs)
        env.reset=counted_reset
        class EmptyObservation:
            metrics={'used_frames':8}
            def __call__(self,e):raise StageFailure('PERCEPTION_FAIL','Test empty sensor packet')
        try:
            r=episode(env,p,c,np.random.default_rng(1045),1,'pudding_box',lambda i:EmptyObservation() if i==0 else ActiveObserver(seed=100045))
            self.assertEqual(len(calls),1)
            self.assertEqual(r['attempt_count'],2)
            self.assertFalse(r['first_attempt_success']);self.assertTrue(r['success'],r)
            np.testing.assert_allclose(r['attempts'][0]['spawn_pose'],r['attempts'][1]['spawn_pose'],atol=1e-12)
            self.assertLessEqual(r['peak_gripper_force_n'],40+1e-6)
        finally:env.close()

    def test_sustained_contact_loss_stops_controller(self):
        env=Environment(Config(),object_names=['pudding_box']);p=Planner(env);c=FeedbackController(env,p)
        try:
            env.reset(np.random.default_rng(43));c.holding=True
            with self.assertRaises(StageFailure):
                for _ in range(25):c.monitor()
            self.assertEqual(c.metrics['contact_loss_stops'],1)
        finally:env.close()


if __name__=='__main__':unittest.main()
