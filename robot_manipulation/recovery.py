"""Bounded recovery in one physical scene, with no reset between attempts."""
import mujoco
import time
import numpy as np
from .pipeline import trial
from .planning import StageFailure
from .robust_obstacles import symmetric_candidates


def safe_withdraw(env, planner, controller):
    controller.gripper(.08)
    target = env.site_pose().copy(); target[2, 3] += .12
    controller.execute(planner.plan(target, True, True), True)
    scratch = mujoco.MjData(env.model)
    scratch.qpos[:] = env.data.qpos
    scratch.qpos[env.arm_qpos] = env.config.home
    mujoco.mj_forward(env.model, scratch)
    home = env.site_pose(scratch).copy()
    controller.execute(planner.plan(home))
    env.step_for(.4)


def episode(env, planner, controller, rng, trial_id, object_id, observer_factory, maximum_attempts=2):
    if not 1 <= maximum_attempts <= 3:
        raise ValueError('Recovery must have a finite 1..3 attempt budget')
    started = time.perf_counter()
    attempts = []; recovery = []; skip = 0
    for index in range(maximum_attempts):
        observer = observer_factory(index)
        result = trial(env, planner, controller, rng, trial_id, object_id=object_id, task='place',
                       candidate_generator=symmetric_candidates, observer=observer,
                       reset_scene=index == 0, candidate_start=skip)
        result['sensing'] = observer.metrics
        if hasattr(env, 'scene_metrics'):
            result['scene_metrics'] = env.scene_metrics()
        attempts.append(result)
        if result['success'] or index + 1 == maximum_attempts:
            break
        stage = result['failure_stage']
        if stage == 'PERCEPTION_FAIL' or (stage == 'PLANNING_FAIL' and not result['executed_stages']):
            recovery.append({'action': 'reobserve', 'after_stage': stage})
        elif stage == 'GRASP_FAIL':
            try:
                safe_withdraw(env, planner, controller)
                skip = result.get('selected_candidate', -1) + 1
                recovery.append({'action': 'withdraw_reobserve_next_grasp', 'after_stage': stage})
            except StageFailure as error:
                recovery.append({'action': 'abort_unsafe_withdrawal', 'stage': error.stage, 'reason': str(error)})
                break
        else:
            recovery.append({'action': 'abort', 'after_stage': stage})
            break
    final = dict(attempts[-1])
    final.update(first_attempt_success=attempts[0]['success'], attempts=attempts, recovery_actions=recovery,
                 attempt_count=len(attempts), spawn_pose=attempts[0]['spawn_pose'],
                 planning_time_s=sum(r['planning_time_s'] for r in attempts),
                 execution_time_s=sum(r['execution_time_s'] for r in attempts),
                 total_time_s=time.perf_counter()-started,
                 observed_frames=sum(r['sensing']['used_frames'] for r in attempts))
    original_height = attempts[0]['spawn_pose'][2][3]
    if final['success'] and final['min_hold_height_m'] <= original_height + env.config.success_height:
        final.update(success=False, failure_stage='SLIP_FAIL', reason='Recovery lift failed original scene height gate')
    final['episode_initial_height_m'] = original_height
    return final
