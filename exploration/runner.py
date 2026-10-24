"""Execute independent topic studies with exactly one scene initialization."""
from dataclasses import asdict
import mujoco
import numpy as np
from robot_manipulation.config import Config
from robot_manipulation.active_sensing import ActiveConfig, ActiveObserver
from robot_manipulation.clutter_planning import ClutterPlanner
from robot_manipulation.control import Controller
from robot_manipulation.recovery import episode
from robot_manipulation.local_grasps import local_candidates
from .workcell import ResearchEnvironment
from .crowding import CrowdedEnvironment
from .manipulation import run_episode
from .sensing import GeometryObserver, PointObserver


def scene_safe(metrics):
    return (metrics['distractor_max_displacement_m'] <= .02 and metrics['unsafe_contact_steps'] == 0
            and metrics['max_target_penetration_m'] <= .001)


def make_environment(case, asset_seed):
    if case['kind'] == 'crowding':
        return CrowdedEnvironment(Config(place_xy=(.48, .30)))
    return ResearchEnvironment(case['kind'], asset_seed, domain=case.get('domain', False))


def run_case_episode(env, case, root_seed, index):
    scene_seed = root_seed+1000+index; sensor_seed = root_seed+100000+index
    if case['kind'] == 'crowding':
        # Balanced shuffled blocks, identical in the single/multiview conditions.
        rng = np.random.default_rng(root_seed)
        names = []
        while len(names) < index:
            names.extend(map(str, rng.permutation(['foam_brick', 'gelatin_box', 'pudding_box'])))
        name = names[index-1]
        reset = env.reset
        def reset_with_visibility(*args, **kwargs):
            pose = reset(*args, **kwargs); env.initial_visibility = env.visibility(); return pose
        env.reset = reset_with_visibility
        settings = ActiveConfig(maximum_views=1) if case['sensing'] == 'single' else ActiveConfig()
        planner = ClutterPlanner(env, seed=root_seed+200000+index)
        row = episode(env, planner, Controller(env, planner), np.random.default_rng(scene_seed), index,
                      name, lambda i:ActiveObserver(settings, sensor_seed,
                       policy='fixed' if case['sensing'] == 'single' else 'active', instance_mask=True),
                      1, candidate_generator=local_candidates)
        metrics = env.scene_metrics()
        row.update(scene_metrics=metrics, visibility=env.initial_visibility, planner_stats=planner.stats,
                   reset_count=env.scene_resets, object_kind='crowding', asset_seed=None,
                   initial_qpos=None, initial_center=np.array(row['spawn_pose'])[:3, 3].tolist(),
                   material={'all_distractors_dynamic': True}, max_edge_strain=0., hinge_excursion_rad=0.,
                   peak_actuator_force_n=row['peak_gripper_force_n'], physical_model='six_YCB_free_bodies_four_obstacles')
        row['first_attempt_success'] = row['attempts'][0]['success'] and scene_safe(metrics)
        if row['success'] and not scene_safe(metrics):
            row.update(success=False, failure_stage='CLUTTER_DISTURBANCE_FAIL')
        row['pairing_state'] = metrics['initial_scene']
    else:
        def observer(index):
            if 'sensing' in case:
                return PointObserver(sensor_seed+1000000*index, case['sensing'],
                                     adverse=case.get('adverse', False), nominal_box=case.get('nominal_box', False))
            return GeometryObserver()
        row = run_episode(env, np.random.default_rng(scene_seed), observer,
                          adaptive=case.get('adaptive', False), recovery=case.get('recovery', False),
                          fault=case.get('fault', False))
        row['pairing_state'] = row['initial_qpos']
        if env.kind == 'novel':
            row['shape_family'] = env.shape
        if env.kind == 'soft':
            row['young_modulus_pa'] = env.young
            row['flex_vertices'] = int(env.model.nflexvert)
            row['elastic_node_dofs'] = int(env.node_qpos.size)
    row.update(trial_id=index, scene_seed=scene_seed, sensor_seed=sensor_seed,
               object_robot_welds=int(np.sum(env.model.eq_type == mujoco.mjtEq.mjEQ_WELD)),
               observation_scope='ideal_mask_known_YCB' if case['kind']=='crowding' else
                    'no_template_no_instance_labels_for_grasp' if 'sensing' in case else
                    'simulation_geometry_to_isolate_mechanics',
               collision_map_scope='simulator_geometry', config=asdict(env.config))
    row['config'].pop('output_dir')
    return row
