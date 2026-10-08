import numpy as np
from .planning import StageFailure
from .transforms import rotation_error


class Controller:
    def __init__(self, env, planner):
        self.env = env
        self.planner = planner

    def gripper(self, width):
        # Official Panda tendon actuator: 0..255 maps to 0..0.08 m aperture.
        self.env.data.ctrl[self.env.gripper_actuator] = np.clip(width / .08 * 255, 0, 255)
        self.env.step_for(.8)

    def execute(self, trajectory, allow_finger_object=False):
        env = self.env
        for a, b, duration in zip(trajectory.joints[:-1], trajectory.joints[1:], trajectory.durations):
            count = max(1, int(np.ceil(duration / env.config.timestep)))
            for tick in range(1, count + 1):
                alpha = tick / count
                smooth = 3 * alpha**2 - 2 * alpha**3
                env.data.ctrl[env.arm_actuators] = a + smooth * (b - a)
                env.step()
                reason = self.planner.forbidden_contacts(env.data, allow_finger_object)
                if reason:
                    raise StageFailure('COLLISION_FAIL', reason)
        for _ in range(round(.4 / env.config.timestep)):
            env.step()
            reason = self.planner.forbidden_contacts(env.data, allow_finger_object)
            if reason:
                raise StageFailure('COLLISION_FAIL', reason)
        error = np.linalg.norm(env.site_pose()[:3, 3] - trajectory.target[:3, 3])
        if error > env.config.tracking_tolerance:
            raise StageFailure('EXECUTION_FAIL', f'End-effector tracking error {error:.4f} m')
        rotation = np.linalg.norm(rotation_error(trajectory.target[:3, :3], env.site_pose()[:3, :3]))
        if rotation > env.config.tracking_rotation_tolerance:
            raise StageFailure('EXECUTION_FAIL', f'End-effector rotation error {rotation:.4f} rad')
