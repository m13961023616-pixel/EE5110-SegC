"""One complete trial, including candidate feasibility, execution and verification."""
import logging
import time
import numpy as np
from .perception import observe
from .grasp import generate_candidates
from .planning import StageFailure
from .evaluation import verify_lift, verify_place

LOG = logging.getLogger('baseline')


def trial(env, planner, controller, rng, trial_id, fixed=False, object_id=None, task='pick', candidate_generator=generate_candidates, observer=observe):
    started = time.perf_counter()
    result = {'trial_id': trial_id, 'object_id': object_id or env.object_id, 'task': task,
              'success': False, 'lift_success': False, 'place_success': False,
              'failure_stage': 'SPAWN_FAIL', 'planning_time_s': 0., 'execution_time_s': 0.}
    stage = 'SPAWN_FAIL'
    try:
        env.reset(rng, fixed, object_id)
        initial_pose = env.object_pose()
        result['spawn_pose'] = initial_pose.tolist()
        stage = 'PERCEPTION_FAIL'
        state = observer(env)
        result.update(estimated_pose=state.pose.tolist(), dimensions_m=state.dimensions.tolist(), mass_kg=env.object_model.mass)
        stage = 'GRASP_GENERATION_FAIL'
        candidates = candidate_generator(state, env.config)
        result['candidate_count'] = len(candidates)
        if not candidates:
            raise StageFailure(stage, 'No candidate fits the gripper width')
        controller.gripper(.08)
        result['candidate_rejections'] = []
        tick = time.perf_counter()
        chosen = None
        for index, candidate in enumerate(candidates):
            try:
                pregrasp = planner.plan(candidate.pregrasp)
                # Check approach from predicted pregrasp before making any motion.
                approach = planner.plan(candidate.pose, cartesian=True, start_q=pregrasp.joints[-1])
                planner.preview_task(candidate, approach, task)
                chosen = (candidate, pregrasp)
                result['selected_candidate'] = index
                break
            except StageFailure as exc:
                result['candidate_rejections'].append({'index': index, 'stage': exc.stage, 'reason': str(exc)})
        result['planning_time_s'] += time.perf_counter() - tick
        if chosen is None:
            raise StageFailure('PLANNING_FAIL', 'All candidate approaches rejected')
        candidate, pregrasp = chosen
        result['grasp_pose'] = candidate.pose.tolist()
        result['gripper_width_m'] = candidate.width

        def execute(name, target=None, cartesian=True, attached=False, trajectory=None, allow_contact=False):
            nonlocal stage
            LOG.info('Trial %d %s: %s', trial_id, env.object_id, name)
            if env.recorder:
                env.recorder.status = name
            if trajectory is None:
                stage = 'PLANNING_FAIL'
                tick = time.perf_counter()
                trajectory = planner.plan(target, cartesian, allow_finger_object=attached or allow_contact, attached=attached)
                result['planning_time_s'] += time.perf_counter() - tick
            stage = 'EXECUTION_FAIL'
            tick = time.perf_counter()
            controller.execute(trajectory, allow_finger_object=attached or allow_contact)
            result['execution_time_s'] += time.perf_counter() - tick

        execute('PRE_GRASP', trajectory=pregrasp)
        execute('APPROACH', candidate.pose)
        stage = 'GRASP_FAIL'
        controller.gripper(0)
        result['grasp_contacts'] = len(env.finger_contacts())
        result['actual_grasp_aperture_m'] = float(np.sum(env.data.qpos[env.finger_qpos]))
        if result['grasp_contacts'] < 2:
            raise StageFailure(stage, 'Both fingers did not contact the object')
        execute('LIFT', candidate.lift, attached=True)
        stage = 'SLIP_FAIL'
        result.update(verify_lift(env, initial_pose[2, 3]))
        result['lift_success'] = result['lift_success'] and result['bilateral_contact_fraction'] >= .95
        if not result['lift_success']:
            raise StageFailure(stage, 'Object did not maintain a stable lift')
        if task == 'place':
            stage = 'PLACE_FAIL'
            # Preserve current relative grasp, transport COM to the target area.
            tick = time.perf_counter()
            transfer, center, rejections = planner.plan_placement()
            result['planning_time_s'] += time.perf_counter() - tick
            result['planned_place_xy'] = center.tolist()
            result['placement_rejections'] = rejections
            execute('TRANSFER', attached=True, trajectory=transfer)
            vertices = env.collision_vertices()
            lower = env.site_pose()
            lower[2, 3] -= vertices[:, 2].min() - env.config.table_top - env.config.place_clearance
            execute('LOWER', lower, attached=True)
            stage = 'PLACE_FAIL'
            controller.gripper(.08)
            retreat = env.site_pose()
            retreat[2, 3] += .12
            execute('RETREAT', retreat, allow_contact=True)
            stage = 'PLACE_FAIL'
            result.update(verify_place(env))
            if not result['place_success']:
                raise StageFailure(stage, 'Released object did not settle inside target')
        result['success'] = True
        result['failure_stage'] = 'SUCCESS'
        if env.recorder:
            env.recorder.status = 'SUCCESS: physical grasp and verified task'
            env.step_for(1.)
    except StageFailure as exc:
        result['failure_stage'], result['reason'] = exc.stage, str(exc)
    except (RuntimeError, ValueError, np.linalg.LinAlgError) as exc:
        result['failure_stage'], result['reason'] = stage, f'{type(exc).__name__}: {exc}'
    result['total_time_s'] = time.perf_counter() - started
    result['peak_gripper_force_n'] = env.max_gripper_force
    LOG.info('Trial %d %s: %s %s', trial_id, env.object_id, result['failure_stage'], result.get('reason', ''))
    return result
