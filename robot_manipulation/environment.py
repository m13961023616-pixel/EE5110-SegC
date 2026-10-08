"""MuJoCo workcell and explicit robot/object identifiers."""
from pathlib import Path
import time
import xml.etree.ElementTree as ET
import mujoco
import numpy as np
from .config import ROOT
from .transforms import transform


class Environment:
    def __init__(self, config, gui=False, realtime=True):
        self.config = config
        model_path = ROOT / 'assets/panda/panda.xml'
        if not model_path.exists():
            raise FileNotFoundError('Run scripts/setup_assets.py before starting the simulation.')
        root = ET.parse(model_path).getroot()
        # The upstream keyframe has only robot qpos; this workcell adds a free body.
        root.remove(root.find('keyframe'))
        root.find('compiler').set('meshdir', str(model_path.parent / 'assets'))
        root.find('option').set('timestep', str(config.timestep))
        root.find('option').set('gravity', '0 0 -9.81')
        visual = ET.SubElement(root, 'visual')
        ET.SubElement(visual, 'global', offwidth='800', offheight='600')
        world = root.find('worldbody')
        ET.SubElement(world, 'geom', name='floor', type='plane', size='2 2 .1',
                      pos='0 0 -.081', rgba='.17 .20 .24 1')
        ET.SubElement(world, 'geom', name='table', type='box', size='.30 .35 .04',
                      pos=f'.5 0 {config.table_top - .04}', rgba='.55 .42 .30 1')
        ET.SubElement(world, 'camera', name='overview', pos='1.3 -1.3 1.1',
                      xyaxes='.707 .707 0 -.35 .35 .87')
        body = ET.SubElement(world, 'body', name='object', pos='.48 0 .022')
        ET.SubElement(body, 'freejoint', name='object_free')
        half = config.object_size / 2
        ET.SubElement(body, 'geom', name='object_geom', type='box',
                      size=f'{half} {half} {half}', mass=str(config.object_mass),
                      friction='1.2 .01 .001', condim='4', rgba='.95 .35 .12 1')
        hand = root.find(".//body[@name='hand']")
        # Site at Panda fingertip pad centre, expressed in the hand frame.
        ET.SubElement(hand, 'site', name='grasp_site', pos='0 0 .1034',
                      size='.006', rgba='0 1 0 1')
        # Keep the official collision geometry; raise finger contact friction.
        for finger_name in ('left_finger', 'right_finger'):
            finger = root.find(f".//body[@name='{finger_name}']")
            for geom in finger.findall('geom'):
                if geom.get('class') != 'visual':
                    geom.set('friction', '1.5 .01 .001')
                    geom.set('condim', '4')
        self.model = mujoco.MjModel.from_xml_string(ET.tostring(root, encoding='unicode'))
        self.data = mujoco.MjData(self.model)
        self.arm_joints = np.array([self.model.joint(f'joint{i}').id for i in range(1, 8)])
        self.arm_qpos = self.model.jnt_qposadr[self.arm_joints]
        self.arm_dofs = self.model.jnt_dofadr[self.arm_joints]
        self.arm_actuators = np.array([self.model.actuator(f'actuator{i}').id for i in range(1, 8)])
        self.gripper_actuator = self.model.actuator('actuator8').id
        self.finger_joints = [self.model.joint(f'finger_joint{i}').id for i in (1, 2)]
        self.finger_qpos = self.model.jnt_qposadr[self.finger_joints]
        self.object_body = self.model.body('object').id
        self.object_geom = self.model.geom('object_geom').id
        self.object_qpos = self.model.jnt_qposadr[self.model.joint('object_free').id]
        self.site = self.model.site('grasp_site').id
        self.finger_bodies = {self.model.body(x).id for x in ('left_finger', 'right_finger')}
        self.robot_bodies = set(range(1, self.object_body))
        self.table_geom = self.model.geom('table').id
        self.floor_geom = self.model.geom('floor').id
        self.viewer = None
        self.realtime = realtime
        if gui:
            from mujoco import viewer as mj_viewer
            self.viewer = mj_viewer.launch_passive(self.model, self.data)
            self.viewer.cam.lookat[:] = [.4, 0, .25]
            self.viewer.cam.distance = 1.7
            self.viewer.cam.azimuth = 135
            self.viewer.cam.elevation = -25

    def reset(self, rng, fixed=False):
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[self.arm_qpos] = self.config.home
        self.data.qpos[self.finger_qpos] = .04
        self.data.ctrl[self.arm_actuators] = self.config.home
        self.data.ctrl[self.gripper_actuator] = 255
        x = .48 if fixed else rng.uniform(*self.config.spawn_x)
        y = 0 if fixed else rng.uniform(*self.config.spawn_y)
        yaw = 0 if fixed else rng.uniform(-np.pi, np.pi)
        start = self.object_qpos
        self.data.qpos[start:start + 7] = [x, y, self.config.table_top + self.config.object_size / 2 + .003,
                                          np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)]
        mujoco.mj_forward(self.model, self.data)
        self.step_for(.6)
        return self.object_pose()

    def object_pose(self):
        return transform(self.data.xmat[self.object_body].reshape(3, 3).copy(),
                         self.data.xpos[self.object_body].copy())

    def site_pose(self, data=None):
        data = self.data if data is None else data
        return transform(data.site_xmat[self.site].reshape(3, 3), data.site_xpos[self.site])

    def step(self):
        start = time.perf_counter()
        mujoco.mj_step(self.model, self.data)
        if not np.all(np.isfinite(self.data.qpos)):
            raise RuntimeError('Non-finite simulation state')
        if self.viewer:
            if not self.viewer.is_running():
                raise KeyboardInterrupt('Viewer closed')
            self.viewer.sync()
            if self.realtime:
                time.sleep(max(0, self.config.timestep - (time.perf_counter() - start)))

    def step_for(self, seconds):
        for _ in range(round(seconds / self.config.timestep)):
            self.step()

    def finger_contacts(self, data=None):
        data = self.data if data is None else data
        touching = set()
        for contact in data.contact[:data.ncon]:
            if contact.dist > .001:
                continue
            g1, g2 = int(contact.geom1), int(contact.geom2)
            if self.object_geom in (g1, g2):
                other = g2 if g1 == self.object_geom else g1
                body = int(self.model.geom_bodyid[other])
                if body in self.finger_bodies:
                    touching.add(body)
        return touching

    def close(self):
        if self.viewer:
            self.viewer.close()
