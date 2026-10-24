"""Physical mechanism checks for new directions, plus no-template isolation."""
from pathlib import Path
import sys
import unittest
import numpy as np
import mujoco
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from exploration.workcell import ResearchEnvironment
from exploration.crowding import CrowdedEnvironment
from exploration.sensing import PointObserver, GeometryObserver
from exploration.manipulation import run_episode
from robot_manipulation.config import Config, ROOT


class ExplorationChecks(unittest.TestCase):
    def test_point_only_unknown_observer_preserves_state_and_cannot_read_template(self):
        e=ResearchEnvironment('novel',seed=2)
        try:
            e.reset(np.random.default_rng(43));saved=e.data.qpos.copy();clock=e.data.time
            def forbidden(*args):raise AssertionError('True pose queried by unknown observer')
            e.object_pose=forbidden;e.object_model=object();e.object_geoms=set()
            observer=PointObserver(100043,'robust',adverse=True);state=observer(e)
            self.assertEqual(observer.metrics['template'],'none')
            self.assertEqual(observer.metrics['source'],'unmasked_range_points')
            self.assertTrue(np.all(state.dimensions>.015))
            np.testing.assert_array_equal(e.data.qpos,saved);self.assertEqual(e.data.time,clock)
        finally:e.close()

    def test_true_flex_deforms_and_is_physically_released(self):
        e=ResearchEnvironment('soft',seed=1)
        try:
            self.assertEqual(e.model.nflex,1);self.assertEqual(e.model.nflexvert,27)
            self.assertEqual(e.node_qpos.size,24)
            r=run_episode(e,np.random.default_rng(43),lambda i:GeometryObserver(),adaptive=True)
            self.assertTrue(r['success'],r)
            self.assertGreater(r['max_edge_strain'],.005);self.assertLessEqual(r['max_edge_strain'],.4)
            self.assertTrue(r['table_contact'] and r['released'])
            self.assertLessEqual(r['peak_actuator_force_n'],40+1e-6)
        finally:e.close()

    def test_passive_hinge_moves_during_whole_assembly_pick_and_place(self):
        e=ResearchEnvironment('articulated',seed=1)
        try:
            r=run_episode(e,np.random.default_rng(43),lambda i:GeometryObserver(),adaptive=True)
            self.assertTrue(r['success'],r);self.assertGreater(r['hinge_excursion_rad'],.02)
            self.assertEqual(e.model.jnt_type[e.lid_joint],mujoco.mjtJoint.mjJNT_HINGE)
        finally:e.close()

    def test_actual_partial_closure_is_detected_and_recovers_without_reset(self):
        e=ResearchEnvironment('rigid',seed=1)
        try:
            r=run_episode(e,np.random.default_rng(43),lambda i:GeometryObserver(),recovery=True,fault=True)
            self.assertTrue(r['success'],r);self.assertFalse(r['first_attempt_success'])
            self.assertEqual(r['reset_count'],1);self.assertEqual(r['attempt_count'],2)
            self.assertEqual(r['attempts'][0]['failure_stage'],'GRASP_FAIL')
            self.assertIn('APPROACH',r['attempts'][0]['executed_stages'])
            self.assertEqual(r['attempts'][0]['closing_contacts'],0)
        finally:e.close()

    def test_randomized_material_is_applied_to_actual_model(self):
        e=ResearchEnvironment('rigid',seed=1,domain=True)
        try:
            e.reset(np.random.default_rng(43))
            mass=float(e.model.body_mass[list(e.target_bodies)].sum())
            self.assertAlmostEqual(mass,e.material['mass_kg']);self.assertNotAlmostEqual(mass,.05)
            self.assertTrue(.30<=e.material['friction']<=.85)
            self.assertEqual(len(e._delay),e.delay_steps)
        finally:e.close()

    def test_dense_visibility_reference_does_not_disable_live_collision(self):
        e=CrowdedEnvironment(Config(place_xy=(.48,.30)))
        try:
            e.reset(np.random.default_rng(1044),object_id='gelatin_box')
            saved=e.model.geom_group.copy();contacts=e.model.geom_contype.copy();q=e.data.qpos.copy()
            visibility=e.visibility()
            self.assertLess(min(visibility['visible_fraction_per_view']),.5)
            self.assertEqual(len(e.active_names),6)
            np.testing.assert_array_equal(saved,e.model.geom_group)
            np.testing.assert_array_equal(contacts,e.model.geom_contype)
            np.testing.assert_array_equal(q,e.data.qpos)
        finally:e.close()

    def test_v21_source_and_frozen_evidence_are_unchanged(self):
        import json
        from clutter_main import source_hash
        old=json.loads((ROOT/'docs/validation/v2.1.0/protocol.json').read_text())
        self.assertEqual(source_hash(),old['source_sha256'])


if __name__=='__main__':unittest.main()
