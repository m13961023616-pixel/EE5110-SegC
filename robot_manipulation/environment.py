"""MuJoCo workcell and explicit robot/object identifiers."""
from pathlib import Path
import time
import xml.etree.ElementTree as ET
import mujoco
import numpy as np
from .config import ROOT
from .transforms import transform
from .dataset import load_object, append_ycb


class Environment:
    def __init__(self, config, gui=False, realtime=True, object_names=None, obstacles=()):
        self.config = config
        self.objects = {name: load_object(name, config) for name in (object_names or ['primitive_cube'])}
        model_path = ROOT / 'assets/panda/panda.xml'
        if not model_path.exists():
            raise FileNotFoundError('Run scripts/setup_assets.py before starting the simulation.')
        root = ET.parse(model_path).getroot()
        # The upstream keyframe has only robot qpos; this workcell adds a free body.
        root.remove(root.find('keyframe'))
        root.find('compiler').set('meshdir', str(model_path.parent / 'assets'))
        root.find('option').set('timestep', str(config.timestep))
        root.find('option').set('gravity', '0 0 -9.81')
        root.find('option').set('cone', 'elliptic')
        root.find('option').set('impratio', str(config.contact_impratio))
        visual = ET.SubElement(root, 'visual')
        ET.SubElement(visual, 'global', offwidth='800', offheight='600')
        world = root.find('worldbody')
        self.obstacles = tuple(obstacles)
        for index, obstacle in enumerate(self.obstacles):
            ET.SubElement(world, 'geom', name=f'obstacle_{index}', type='box',
                          pos=' '.join(map(str, obstacle['center'])),
                          size=' '.join(map(str, obstacle['half_size'])),
                          rgba='.28 .42 .62 1', friction='1.2 .01 .001')
        ET.SubElement(world, 'geom', name='floor', type='plane', size='2 2 .1',
                      pos='0 0 -.081', rgba='.17 .20 .24 1')
        ET.SubElement(world, 'geom', name='table', type='box', size='.30 .35 .04',
                      pos=f'.5 0 {config.table_top - .04}', rgba='.55 .42 .30 1')
        ET.SubElement(world, 'camera', name='overview', pos='1.3 -1.3 1.1',
                      xyaxes='.707 .707 0 -.35 .35 .87')
        ET.SubElement(world, 'site', name='place_target', pos='.48 .22 .002',
                      type='box', size='.085 .075 .001', rgba='.2 .7 .3 .35')
        for name, object_model in self.objects.items():
            if name == 'primitive_cube':
                body = ET.SubElement(world, 'body', name='object', pos='.48 0 .022')
                ET.SubElement(body, 'freejoint', name='object_free')
                half = config.object_size / 2
                ET.SubElement(body, 'geom', name='object_geom', type='box',
                              size=f'{half} {half} {half}', mass=str(config.object_mass),
                              friction='1.2 .01 .001', condim='4', rgba='.95 .35 .12 1')
            else:
                append_ycb(root, world, object_model)
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
        # Preserve 0..255 aperture mapping, with an explicit bounded grip force.
        aid = self.gripper_actuator
        self.model.actuator_gainprm[aid, 0] = .04 * config.gripper_stiffness / 255
        self.model.actuator_biasprm[aid, 1] = -config.gripper_stiffness
        self.model.actuator_forcerange[aid] = [-config.gripper_force_limit, config.gripper_force_limit]
        self.finger_joints = [self.model.joint(f'finger_joint{i}').id for i in (1, 2)]
        self.finger_qpos = self.model.jnt_qposadr[self.finger_joints]
        self.object_ids = {}
        for name in self.objects:
            body_name = 'object' if name == 'primitive_cube' else f'object_{name}'
            joint_name = 'object_free' if name == 'primitive_cube' else f'object_free_{name}'
            bid = self.model.body(body_name).id
            adr = self.model.jnt_qposadr[self.model.joint(joint_name).id]
            geoms = np.flatnonzero(self.model.geom_bodyid == bid)
            self.object_ids[name] = (bid, adr, geoms)
        self._original_contype = self.model.geom_contype.copy()
        self._original_conaffinity = self.model.geom_conaffinity.copy()
        self._original_rgba = self.model.geom_rgba.copy()
        self.activate_object(next(iter(self.objects)))
        self.site = self.model.site('grasp_site').id
        self.finger_bodies = {self.model.body(x).id for x in ('left_finger', 'right_finger')}
        self.robot_bodies = set(range(1, min(x[0] for x in self.object_ids.values())))
        self.table_geom = self.model.geom('table').id
        self.floor_geom = self.model.geom('floor').id
        self.viewer = None
        self.recorder = None
        self.max_gripper_force = 0.
        self.realtime = realtime
        if gui:
            from mujoco import viewer as mj_viewer
            self.viewer = mj_viewer.launch_passive(self.model, self.data)
            self.viewer.cam.lookat[:] = [.4, 0, .25]
            self.viewer.cam.distance = 1.7
            self.viewer.cam.azimuth = 135
            self.viewer.cam.elevation = -25

    def activate_object(self, name):
        self.object_id = name
        self.object_model = self.objects[name]
        self.object_body, self.object_qpos, geoms = self.object_ids[name]
        self.object_geoms = {int(g) for g in geoms if self._original_contype[g] != 0}
        self.object_geom = min(self.object_geoms)
        for other, (body, _, indices) in self.object_ids.items():
            active = other == name
            self.model.body_gravcomp[body] = 0 if active else 1
            self.model.geom_contype[indices] = self._original_contype[indices] if active else 0
            self.model.geom_conaffinity[indices] = self._original_conaffinity[indices] if active else 0
            self.model.geom_rgba[indices] = self._original_rgba[indices]
            if not active:
                self.model.geom_rgba[indices, 3] = 0

    def reset(self, rng, fixed=False, object_id=None):
        self.activate_object(object_id or self.object_id)
        self.max_gripper_force = 0.
        mujoco.mj_resetData(self.model, self.data)
        if self.recorder:
            self.recorder.reset_time()
        for _, adr, _ in self.object_ids.values():
            self.data.qpos[adr:adr + 7] = [-5, -5, -5, 1, 0, 0, 0]
        self.data.qpos[self.arm_qpos] = self.config.home
        self.data.qpos[self.finger_qpos] = .04
        self.data.ctrl[self.arm_actuators] = self.config.home
        self.data.ctrl[self.gripper_actuator] = 255
        x = .48 if fixed else rng.uniform(*self.config.spawn_x)
        y = 0 if fixed else rng.uniform(*self.config.spawn_y)
        yaw = 0 if fixed else rng.uniform(-np.pi, np.pi)
        start = self.object_qpos
        # Packaging rests upright on its narrow end; native metric scale is unchanged.
        roll = (np.pi / 2 if self.object_id == 'gelatin_box' else
                -np.pi / 2 if self.object_id == 'pudding_box' else 0.)
        rotation = np.array([[1, 0, 0], [0, np.cos(roll), -np.sin(roll)],
                             [0, np.sin(roll), np.cos(roll)]])
        bottom = (self.object_model.vertices @ rotation.T)[:, 2].min()
        quaternion = [np.cos(yaw / 2) * np.cos(roll / 2),
                      np.cos(yaw / 2) * np.sin(roll / 2),
                      np.sin(yaw / 2) * np.sin(roll / 2),
                      np.sin(yaw / 2) * np.cos(roll / 2)]
        self.data.qpos[start:start + 7] = [x, y, self.config.table_top - bottom + .004, *quaternion]
        mujoco.mj_forward(self.model, self.data)
        self.step_for(.6)
        dof = self.model.jnt_dofadr[self.model.body_jntadr[self.object_body]]
        for _ in range(8):
            if np.linalg.norm(self.data.qvel[dof:dof + 6]) < .05:
                break
            self.step_for(.2)
        if np.linalg.norm(self.data.qvel[dof:dof + 6]) > .5:
            raise RuntimeError('Object has not settled on the table')
        return self.object_pose()

    def object_pose(self, data=None):
        data = self.data if data is None else data
        return transform(data.xmat[self.object_body].reshape(3, 3).copy(),
                         data.xpos[self.object_body].copy())

    def site_pose(self, data=None):
        data = self.data if data is None else data
        return transform(data.site_xmat[self.site].reshape(3, 3), data.site_xpos[self.site])

    def step(self):
        start = time.perf_counter()
        self.data.qfrc_applied[self.arm_dofs] = (self.data.qfrc_bias[self.arm_dofs]
                                               if self.config.gravity_compensation else 0.)
        mujoco.mj_step(self.model, self.data)
        self.max_gripper_force = max(self.max_gripper_force,
                                     abs(float(self.data.actuator_force[self.gripper_actuator])))
        if self.recorder:
            self.recorder.capture()
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

    def collision_vertices(self, data=None):
        """World vertices of the actual compiled collision geometry, not texture mesh."""
        data = self.data if data is None else data
        vertices = []
        for g in self.object_geoms:
            mesh = self.model.geom_dataid[g]
            if self.model.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH:
                start, count = self.model.mesh_vertadr[mesh], self.model.mesh_vertnum[mesh]
                local = self.model.mesh_vert[start:start + count]
            elif self.model.geom_type[g] == mujoco.mjtGeom.mjGEOM_BOX:
                local = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1)
                                  for z in (-1, 1)]) * self.model.geom_size[g]
            else:
                raise ValueError('Unsupported collision geometry')
            vertices.append(local @ data.geom_xmat[g].reshape(3, 3).T + data.geom_xpos[g])
        return np.vstack(vertices)

    def finger_contacts(self, data=None):
        data = self.data if data is None else data
        touching = set()
        for contact in data.contact[:data.ncon]:
            if contact.dist > .001:
                continue
            g1, g2 = int(contact.geom1), int(contact.geom2)
            if g1 in self.object_geoms or g2 in self.object_geoms:
                other = g2 if g1 in self.object_geoms else g1
                body = int(self.model.geom_bodyid[other])
                if body in self.finger_bodies:
                    touching.add(body)
        return touching

    def close(self):
        if self.recorder:
            self.recorder.close()
        if self.viewer:
            self.viewer.close()
