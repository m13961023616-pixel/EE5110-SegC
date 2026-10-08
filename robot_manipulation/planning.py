"""Damped Jacobian IK plus checked, time-parameterized baseline paths.

This structured planner rejects obstructed paths; it does not search around obstacles.
Collision tests sample interpolated joint configurations (not a continuous guarantee).
"""
from dataclasses import dataclass
import mujoco
import numpy as np
from .transforms import rotation_error


class StageFailure(RuntimeError):
    def __init__(self, stage, reason):
        self.stage = stage
        super().__init__(reason)


@dataclass
class Trajectory:
    joints: list
    durations: list
    target: np.ndarray


class Planner:
    def __init__(self, env):
        self.env = env
        self.scratch = mujoco.MjData(env.model)
        self.limits = env.model.jnt_range[env.arm_joints]

    def prepare(self):
        self.scratch.qpos[:] = self.env.data.qpos
        self.scratch.qvel[:] = 0

    def ik(self, target, seed):
        env, data = self.env, self.scratch
        q = np.asarray(seed).copy()
        jp, jr = np.zeros((3, env.model.nv)), np.zeros((3, env.model.nv))
        for _ in range(500):
            data.qpos[env.arm_qpos] = q
            mujoco.mj_forward(env.model, data)
            pose = env.site_pose(data)
            position = target[:3, 3] - pose[:3, 3]
            orientation = rotation_error(target[:3, :3], pose[:3, :3])
            if np.linalg.norm(position) < env.config.position_tolerance and np.linalg.norm(orientation) < env.config.rotation_tolerance:
                return q
            mujoco.mj_jacSite(env.model, data, jp, jr, env.site)
            jac = np.vstack((jp[:, env.arm_dofs], .4 * jr[:, env.arm_dofs]))
            error = np.concatenate((position, .4 * orientation))
            delta = jac.T @ np.linalg.solve(jac @ jac.T + .025**2 * np.eye(6), error)
            delta *= min(1., .12 / max(np.max(np.abs(delta)), 1e-9))
            q = np.clip(q + delta, self.limits[:, 0] + .005, self.limits[:, 1] - .005)
        raise StageFailure('IK_FAIL', f'IK did not converge; position error {np.linalg.norm(position):.4f} m')

    def forbidden_contacts(self, data, allow_finger_object=False):
        env = self.env
        for contact in data.contact[:data.ncon]:
            if contact.dist >= -.0005:
                continue
            g1, g2 = int(contact.geom1), int(contact.geom2)
            b1, b2 = int(env.model.geom_bodyid[g1]), int(env.model.geom_bodyid[g2])
            robot1, robot2 = b1 in env.robot_bodies, b2 in env.robot_bodies
            if not (robot1 or robot2):
                continue
            if robot1 and robot2:
                return f'robot self contact: bodies {b1}, {b2}'
            robot_body = b1 if robot1 else b2
            other_geom = g2 if robot1 else g1
            if other_geom == env.floor_geom and robot_body == env.model.body('link0').id:
                continue
            if allow_finger_object and other_geom in env.object_geoms and robot_body in env.finger_bodies:
                continue
            return f'forbidden contact: body {robot_body}, geom {other_geom}'
        return None

    def validate(self, points, allow_finger_object=False, attached=False):
        env, data = self.env, self.scratch
        initial_object = env.object_pose()
        initial_site = env.site_pose()
        relative = np.linalg.inv(initial_site) @ initial_object
        for a, b in zip(points[:-1], points[1:]):
            samples = max(2, int(np.ceil(np.max(np.abs(b - a)) / .015)) + 1)
            for alpha in np.linspace(0, 1, samples):
                data.qpos[:] = env.data.qpos
                data.qpos[env.arm_qpos] = (1 - alpha) * a + alpha * b
                mujoco.mj_forward(env.model, data)
                if attached:
                    pose = env.site_pose(data) @ relative
                    adr = env.object_qpos
                    data.qpos[adr:adr + 3] = pose[:3, 3]
                    quat = np.zeros(4)
                    mujoco.mju_mat2Quat(quat, pose[:3, :3].ravel())
                    data.qpos[adr + 3:adr + 7] = quat
                    mujoco.mj_forward(env.model, data)
                    # Transported object may touch support at the start, but never penetrate it.
                    for contact in data.contact[:data.ncon]:
                        if (contact.geom1 in env.object_geoms or contact.geom2 in env.object_geoms) and contact.dist < -.001:
                            other = contact.geom2 if contact.geom1 in env.object_geoms else contact.geom1
                            if int(env.model.geom_bodyid[other]) not in env.finger_bodies:
                                raise StageFailure('COLLISION_FAIL', 'Transported object intersects environment')
                reason = self.forbidden_contacts(data, allow_finger_object)
                if reason:
                    raise StageFailure('COLLISION_FAIL', reason)

    def plan(self, target, cartesian=False, allow_finger_object=False, attached=False, start_q=None):
        self.prepare()
        env = self.env
        start_q = env.data.qpos[env.arm_qpos].copy() if start_q is None else np.asarray(start_q).copy()
        points = [start_q]
        self.scratch.qpos[env.arm_qpos] = start_q
        mujoco.mj_forward(env.model, self.scratch)
        start_pose = env.site_pose(self.scratch)
        if cartesian:
            count = max(2, int(np.ceil(np.linalg.norm(target[:3, 3] - start_pose[:3, 3]) / .006)))
            # Approach/lift preserve the current grasp orientation.
            for alpha in np.linspace(0, 1, count + 1)[1:]:
                waypoint = target.copy()
                waypoint[:3, 3] = (1 - alpha) * start_pose[:3, 3] + alpha * target[:3, 3]
                points.append(self.ik(waypoint, points[-1]))
        else:
            points.append(self.ik(target, start_q))
        self.validate(points, allow_finger_object, attached)
        # Cubic smoothstep peak speed is 1.5 * delta / duration.
        durations = [max(.12,
                         1.5 * np.max(np.abs(b - a)) / env.config.max_joint_speed,
                         np.sqrt(6 * np.max(np.abs(b - a)) / env.config.max_joint_acceleration))
                     for a, b in zip(points[:-1], points[1:])]
        return Trajectory(points, durations, target)
