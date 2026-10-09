"""Contact-force feedback with actuator bounds and sustained contact-loss stop."""
import mujoco
import numpy as np
from .control import Controller
from .planning import StageFailure


def finger_normal_forces(env):
    forces = {body: 0. for body in env.finger_bodies}
    wrench = np.zeros(6)
    for index, contact in enumerate(env.data.contact[:env.data.ncon]):
        if contact.geom1 in env.object_geoms or contact.geom2 in env.object_geoms:
            other = contact.geom2 if contact.geom1 in env.object_geoms else contact.geom1
            body = int(env.model.geom_bodyid[other])
            if body in forces:
                mujoco.mj_contactForce(env.model, env.data, index, wrench)
                forces[body] += max(0., float(wrench[0]))
    return forces


class FeedbackController(Controller):
    def __init__(self, env, planner):
        super().__init__(env, planner)
        self.holding = False
        self.demand = env.config.grip_preload
        self.lost_steps = 0
        self.metrics = {'adjustments': 0, 'maximum_contact_loss_steps': 0, 'contact_loss_stops': 0}

    def gripper(self, width):
        self.holding = False
        self.lost_steps = 0
        if width > 0:
            self.demand = self.env.config.grip_preload
        super().gripper(width)
        self.holding = width == 0 and len(self.env.finger_contacts()) == 2

    def monitor(self):
        if not self.holding:
            return
        env = self.env
        forces = finger_normal_forces(env)
        bilateral = len(env.finger_contacts()) == 2
        self.lost_steps = 0 if bilateral else self.lost_steps + 1
        self.metrics['maximum_contact_loss_steps'] = max(self.metrics['maximum_contact_loss_steps'], self.lost_steps)
        if self.lost_steps >= round(.04 / env.config.timestep):
            self.metrics['contact_loss_stops'] += 1
            raise StageFailure('SLIP_DETECTED', 'Sustained loss of bilateral contact during transport')
        if bilateral and min(forces.values()) < 4. and self.demand < 32.:
            self.demand = min(32., self.demand + .02)
            opening = float(np.mean(env.data.qpos[env.finger_qpos]))
            gain = env.model.actuator_gainprm[env.gripper_actuator, 0]
            env.data.ctrl[env.gripper_actuator] = np.clip((env.config.gripper_stiffness * opening - self.demand) / gain, 0, 255)
            self.metrics['adjustments'] += 1

    def execute(self, trajectory, allow_finger_object=False):
        original_step = self.env.step
        def monitored_step():
            original_step()
            self.monitor()
        self.env.step = monitored_step
        try:
            return super().execute(trajectory, allow_finger_object)
        finally:
            self.env.step = original_step
