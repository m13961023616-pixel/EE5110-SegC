"""Contact-aware execution and one-scene physical failure recovery."""
import time
import mujoco
import numpy as np
from robot_manipulation.control import Controller
from robot_manipulation.grasp import generate_candidates
from robot_manipulation.planning import Planner, StageFailure
from robot_manipulation.robust_obstacles import symmetric_candidates
from robot_manipulation.grasp import GraspCandidate
from robot_manipulation.transforms import top_rotation, transform


def measured_candidates(state, config):
    """Top approaches using measured support, with no vertex-count shape classifier."""
    vertices = state.vertices @ state.pose[:3, :3].T + state.pose[:3, 3]
    low, high = vertices.min(axis=0), vertices.max(axis=0)
    center = (low+high)/2
    center[2] = max(low[2]+.017, low[2]+.55*(high[2]-low[2]), high[2]-.025)
    yaw = float(np.arctan2(state.pose[1, 0], state.pose[0, 0]))
    result = []
    for shift in (0., .008, -.008):
        for angle in (0., np.pi/2, np.pi/12, -np.pi/12):
            for symmetry in (0., np.pi):
                normalized = (yaw+angle+np.pi/2) % np.pi-np.pi/2
                rotation = top_rotation(normalized+symmetry)
                width = float(np.ptp(vertices @ rotation[:, 1])+.006)
                if width > .080:
                    continue
                point = center+shift*rotation[:, 0]
                pose = transform(rotation, point); pre, lift = pose.copy(), pose.copy()
                pre[:3, 3] -= rotation[:, 2]*config.pregrasp_clearance
                lift[2, 3] += config.lift_distance
                result.append(GraspCandidate(pose, pre, lift, width))
    return result


class ResearchPlanner(Planner):
    def spawn(self, state):
        return ResearchPlanner(self.env, state)

    def validate(self, points, allow_finger_object=False, attached=False):
        if self.env.kind != 'soft' or not attached:
            return super().validate(points, allow_finger_object, attached)
        env, data = self.env, self.scratch
        initial_site = env.site_pose(self.state)
        nodes = env.model.body_pos[env.node_bodies] + self.state.qpos[env.node_qpos]
        local = (nodes-initial_site[:3, 3]) @ initial_site[:3, :3]
        for a, b in zip(points[:-1], points[1:]):
            count = max(2, int(np.ceil(np.max(np.abs(b-a))/.015))+1)
            for alpha in np.linspace(0, 1, count):
                data.qpos[:] = self.state.qpos
                data.qpos[env.arm_qpos] = (1-alpha)*a+alpha*b
                mujoco.mj_forward(env.model, data)
                site = env.site_pose(data)
                predicted = local @ site[:3, :3].T + site[:3, 3]
                data.qpos[env.node_qpos] = predicted-env.model.body_pos[env.node_bodies]
                mujoco.mj_forward(env.model, data)
                reason = self.forbidden_contacts(data, allow_finger_object)
                if reason:
                    raise StageFailure('COLLISION_FAIL', reason)
                for contact in data.contact[:data.ncon]:
                    if env.target_contact(contact):
                        other = env.other_geom(contact)
                        if other >= 0 and env.model.geom_bodyid[other] not in env.finger_bodies and contact.dist < -.001:
                            raise StageFailure('COLLISION_FAIL', 'Predicted elastic target intersects workcell')

    def forbidden_contacts(self, data, allow_finger_object=False):
        env = self.env
        for contact in data.contact[:data.ncon]:
            if contact.dist >= -.0005:
                continue
            if env.target_contact(contact):
                other = env.other_geom(contact)
                if other < 0:
                    continue
                body = int(env.model.geom_bodyid[other])
                if body not in env.robot_bodies:
                    continue
                if allow_finger_object and body in env.finger_bodies:
                    continue
                return 'Robot contacts target outside allowed finger contact'
            g1, g2 = map(int, contact.geom)
            if min(g1, g2) < 0:
                continue
            b1, b2 = map(int, env.model.geom_bodyid[[g1, g2]])
            r1, r2 = b1 in env.robot_bodies, b2 in env.robot_bodies
            if not (r1 or r2):
                continue
            body, other = (b1, g2) if r1 else (b2, g1)
            if other == env.floor_geom and body == env.model.body('link0').id:
                continue
            return 'Robot self/workcell collision'
        return None


class ContactController(Controller):
    def __init__(self, env, planner, adaptive=False, jam_first=False):
        super().__init__(env, planner)
        self.adaptive, self.jam_first = adaptive, jam_first
        self.closed = False; self.close_calls = 0
        self.demand = 4.; self.lost = 0
        self.metrics = {'feedback_adjustments': 0, 'contact_loss_stops': 0, 'injected_partial_closures': 0}

    def regulate(self):
        if not self.closed:
            return
        forces = self.env.contact_forces()
        bilateral = len(self.env.finger_contacts()) == 2
        self.lost = 0 if bilateral else self.lost + 1
        if self.lost > round(.06/self.env.config.timestep):
            self.metrics['contact_loss_stops'] += 1
            raise StageFailure('SLIP_DETECTED', 'Bilateral physical contact lost for 60 ms')
        if self.adaptive and bilateral:
            target = 1.25 if self.env.kind == 'soft' else 5.
            error = target-min(forces.values())
            new = float(np.clip(self.demand + error*self.env.config.timestep*10., .5, 32.))
            self.metrics['feedback_adjustments'] += int(abs(new-self.demand) > 1e-5)
            self.demand = new
            env = self.env
            opening = float(np.mean(env.data.qpos[env.finger_qpos]))
            env.data.ctrl[env.gripper_actuator] = np.clip(
                (env.config.gripper_stiffness*opening-self.demand)/env.model.actuator_gainprm[env.gripper_actuator, 0], 0, 255)

    def gripper(self, width):
        self.closed = False; self.lost = 0
        if width == 0:
            self.close_calls += 1
            if self.jam_first and self.close_calls == 1:
                self.metrics['injected_partial_closures'] += 1
                # Physical actuator command fault: jaws stay wider than the 40 mm target.
                # Contacts and success flags are never forged; the fault is transient and logged.
                return super().gripper(.058)
        super().gripper(width)
        self.closed = width == 0 and len(self.env.finger_contacts()) == 2
        if self.closed:
            self.demand = 4.
            for _ in range(round(.25/self.env.config.timestep)):
                self.env.step(); self.regulate()

    def execute(self, trajectory, allow_finger_object=False):
        step = self.env.step
        def regulated_step():
            step(); self.regulate()
        self.env.step = regulated_step
        try:
            return super().execute(trajectory, allow_finger_object)
        finally:
            self.env.step = step


def withdraw(env, planner, controller):
    controller.gripper(.08)
    pose = env.site_pose(); pose[2, 3] += .12
    controller.execute(planner.plan(pose, True, True), True)
    scratch = mujoco.MjData(env.model); scratch.qpos[:] = env.data.qpos
    scratch.qpos[env.arm_qpos] = env.config.home
    mujoco.mj_forward(env.model, scratch)
    controller.execute(planner.plan(env.site_pose(scratch)))
    env.step_for(.4)


def attempt(env, planner, controller, observer, reference_height):
    row = {'success': False, 'failure_stage': 'PERCEPTION_FAIL', 'executed_stages': [], 'candidate_rejections': []}
    stage = 'PERCEPTION_FAIL'
    try:
        state = observer(env)
        row['estimated_pose'] = state.pose.tolist()
        candidates = measured_candidates(state, env.config)
        row['candidate_count'] = len(candidates)
        controller.gripper(.08)
        chosen = None
        for index, candidate in enumerate(candidates):
            try:
                pregrasp = planner.plan(candidate.pregrasp)
                approach = planner.plan(candidate.pose, True, start_q=pregrasp.joints[-1])
                if env.kind != 'soft':
                    planner.preview_task(candidate, approach, 'place')
                chosen = candidate, pregrasp
                row['selected_candidate'] = index
                break
            except StageFailure as error:
                row['candidate_rejections'].append({'index': index, 'stage': error.stage, 'reason': str(error)})
        if chosen is None:
            raise StageFailure('PLANNING_FAIL', 'All measured-geometry candidates rejected')
        candidate, pregrasp = chosen
        for name, pose, path in [('PRE_GRASP', None, pregrasp), ('APPROACH', candidate.pose, None)]:
            row['executed_stages'].append(name)
            if env.recorder: env.recorder.status = name
            controller.execute(path if path is not None else planner.plan(pose, True))
        stage = 'GRASP_FAIL'; controller.gripper(0)
        row['closing_contacts'] = len(env.finger_contacts())
        if row['closing_contacts'] != 2:
            raise StageFailure(stage, 'Both physical fingers did not contact target')
        if hasattr(env, 'capture_event'): env.capture_event('grasp')
        row['executed_stages'].append('LIFT')
        if env.recorder: env.recorder.status = 'LIFT'
        controller.execute(planner.plan(candidate.lift, True, True, True), True)
        stage = 'SLIP_FAIL'; heights = []; contacts = []
        for _ in range(round(1./env.config.timestep)):
            env.step(); controller.regulate()
            heights.append(float(env.target_center()[2])); contacts.append(len(env.finger_contacts()) == 2)
        row.update(min_hold_height_m=min(heights), bilateral_contact_fraction=float(np.mean(contacts)))
        if min(heights) <= reference_height+.08 or np.mean(contacts) < .95:
            raise StageFailure(stage, 'Original-height/bilateral hold gate failed')
        if hasattr(env, 'capture_event'): env.capture_event('lift')
        stage = 'TRANSFER_FAIL'
        transfer = env.site_pose(); transfer[:2, 3] += np.array(env.config.place_xy)-env.target_center()[:2]
        row['executed_stages'].append('TRANSFER')
        if env.recorder: env.recorder.status = 'TRANSFER'
        controller.execute(planner.plan(transfer, True, True, True), True)
        lower = env.site_pose(); lower[2, 3] -= env.collision_vertices()[:, 2].min()-.008
        row['executed_stages'].append('LOWER')
        if env.recorder: env.recorder.status = 'LOWER'
        controller.execute(planner.plan(lower, True, True, True), True)
        stage = 'PLACE_FAIL'; controller.gripper(.08)
        retreat = env.site_pose(); retreat[2, 3] += .12
        controller.execute(planner.plan(retreat, True, True), True)
        row['executed_stages'].append('RETREAT'); env.step_for(1.)
        distance = float(np.linalg.norm(env.target_center()[:2]-env.config.place_xy))
        speed = float(np.linalg.norm(env.target_velocity()))
        row.update(place_distance_m=distance, final_speed_m_s=speed, released=not env.finger_contacts(),
                   table_contact=env.table_contact())
        if not (distance < .055 and speed < .02 and row['released'] and row['table_contact']):
            raise StageFailure(stage, 'Release/support/destination/settling gate failed')
        if env.kind == 'soft' and env.max_strain > .40:
            raise StageFailure('DEFORMATION_LIMIT', 'Elastic edge strain exceeds frozen 40% limit')
        row.update(success=True, failure_stage='SUCCESS')
        if hasattr(env, 'capture_event'): env.capture_event('place')
    except StageFailure as error:
        row.update(failure_stage=error.stage, reason=str(error))
    row['sensing'] = dict(observer.metrics)
    return row


def run_episode(env, rng, observer_factory, adaptive=False, recovery=False, fault=False):
    started = time.perf_counter(); env.reset(rng)
    reference = float(env.target_center()[2]); original = env.data.qpos.copy()
    planner = ResearchPlanner(env); controller = ContactController(env, planner, adaptive, fault)
    attempts = []; actions = []
    for index in range(2 if recovery else 1):
        result = attempt(env, planner, controller, observer_factory(index), reference)
        attempts.append(result)
        if result['success'] or not recovery or index == 1:
            break
        if result['failure_stage'] not in ('GRASP_FAIL', 'PERCEPTION_FAIL', 'PLANNING_FAIL'):
            break
        if result['executed_stages']:
            try:
                withdraw(env, planner, controller); actions.append('checked_open_withdraw_home_reobserve')
            except StageFailure as error:
                actions.append('abort_unsafe_withdrawal:'+str(error)); break
        else:
            actions.append('reobserve_before_motion')
    row = dict(attempts[-1])
    row.update(first_attempt_success=attempts[0]['success'], attempts=attempts, recovery_actions=actions,
               attempt_count=len(attempts), reset_count=env.reset_count,
               initial_qpos=original.tolist(), initial_center=env.initial_center.tolist(),
               reference_height_m=reference, object_kind=env.kind, asset_seed=env.asset_seed,
               material=env.material, physical_model='Saint_Venant_Kirchhoff_trilinear_flex' if env.kind == 'soft' else 'hinged_assembly' if env.kind == 'articulated' else 'rigid_procedural',
               max_edge_strain=env.max_strain, max_finger_normal_force_n=env.max_contact_force,
               peak_actuator_force_n=env.max_gripper_force, controller=controller.metrics,
               hinge_excursion_rad=float(np.ptp(env.lid_angles)) if env.lid_angles else 0.,
               total_time_s=time.perf_counter()-started)
    if env.recorder:
        env.recorder.status = row['failure_stage']; env.step_for(1.)
    return row
