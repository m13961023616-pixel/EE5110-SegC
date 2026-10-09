"""Real simultaneous distractors, paired resets, scene gates and target sensing."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from robot_manipulation.clutter import ClutterEnvironment, compound_obstacles
from robot_manipulation.config import Config
from robot_manipulation.active_sensing import ActiveObserver
from robot_manipulation.clutter_planning import ClutterPlanner
from robot_manipulation.feedback import FeedbackController
from robot_manipulation.recovery import episode


def environment(count=3):
    return ClutterEnvironment(Config(place_xy=(.48,.30)),distractors=count,obstacles=compound_obstacles())


class ClutterChecks(unittest.TestCase):
    def test_distractors_keep_gravity_collision_and_seeded_pose(self):
        e=environment(5)
        try:
            e.reset(np.random.default_rng(1044),object_id='gelatin_box')
            self.assertEqual(len(e.active_names),6)
            first=e.scene_metrics()['initial_scene']
            for n in e.distractor_names:
                body,_,ids=e.object_ids[n]
                self.assertEqual(e.model.body_gravcomp[body],0)
                self.assertTrue(np.any(e.model.geom_contype[ids]!=0))
                self.assertGreater(e.body_pose(n)[0,3],.2)
            e.reset(np.random.default_rng(1044),object_id='gelatin_box')
            for n in e.active_names:np.testing.assert_array_equal(first[n],e.scene_metrics()['initial_scene'][n])
        finally:e.close()

    def test_neighbor_motion_is_recorded_as_a_scene_gate(self):
        e=environment()
        try:
            e.reset(np.random.default_rng(1044),object_id='gelatin_box')
            name=e.distractor_names[0];_,adr,_=e.object_ids[name]
            # Deliberate test perturbation, not a manipulation implementation.
            e.data.qpos[adr]+=.03;e.step()
            self.assertGreater(e.scene_metrics()['distractor_max_displacement_m'],.02)
        finally:e.close()

    def test_instance_observation_never_falls_back_to_pose(self):
        e=environment()
        try:
            e.reset(np.random.default_rng(1044),object_id='gelatin_box')
            o=ActiveObserver(seed=100044,instance_mask=True);o(e)
            self.assertEqual(o.metrics['segmentation'],'ideal_simulation_instance_mask')
            self.assertLess(o.metrics['used_frames'],64)
            self.assertTrue(o.metrics['accepted'])
        finally:e.close()

    def test_contact_based_transparent_clutter_release(self):
        e=environment();p=ClutterPlanner(e,seed=200044);c=FeedbackController(e,p)
        try:
            r=episode(e,p,c,np.random.default_rng(1044),1,'gelatin_box',lambda i:ActiveObserver(seed=100044+i*1000000,instance_mask=True))
            self.assertTrue(r['success'],r)
            self.assertEqual(e.scene_resets,1)
            self.assertTrue(r['released'] and r['place_table_contact'])
            self.assertEqual(e.scene_metrics()['unsafe_contact_steps'],0)
            self.assertLess(e.scene_metrics()['distractor_max_displacement_m'],.02)
        finally:e.close()

    def test_initial_transit_ik_failure_can_use_clearance_waypoints(self):
        e=environment();p=ClutterPlanner(e,seed=200046);c=FeedbackController(e,p)
        try:
            r=episode(e,p,c,np.random.default_rng(1046),1,'foam_brick',lambda i:ActiveObserver(seed=100046+i*1000000,instance_mask=True))
            self.assertTrue(r['success'],r)
            self.assertTrue(any(s['method']=='compound_clearance' and s['success'] for s in p.stats))
            self.assertEqual(e.scene_metrics()['unsafe_contact_steps'],0)
        finally:e.close()


if __name__=='__main__':unittest.main()
