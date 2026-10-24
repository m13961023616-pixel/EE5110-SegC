"""Procedural held-out solids, a passive hinge and a genuine elastic flex solid."""
from collections import deque
from dataclasses import replace
from itertools import product
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
import mujoco
import numpy as np
from robot_manipulation.config import Config, ROOT
from robot_manipulation.dataset import ObjectModel
from robot_manipulation.environment import Environment
from robot_manipulation.transforms import transform


def corners(size):
    return np.array(list(product((-1., 1.), repeat=3))) * size


class ResearchEnvironment(Environment):
    def __init__(self, kind='novel', seed=0, domain=False, **kwargs):
        self.kind, self.asset_seed, self.domain = kind, seed, domain
        self.monitoring = False
        self.reset_count = 0
        self._delay = deque()
        self.delay_steps = 0
        config = Config(spawn_x=(.43, .51), spawn_y=(-.09, .015),
                        place_xy=(.48, .22), grip_preload=4.)
        super().__init__(config, **kwargs)
        folder = ROOT / 'outputs/exploration_model_cache'; folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=folder) as temporary:
            xml = Path(temporary) / 'workcell.xml'
            mujoco.mj_saveLastXML(str(xml), self.model)
            root = ET.parse(xml).getroot()
        rng = np.random.default_rng(seed)
        root.find('compiler').set('angle', 'radian')
        body = root.find("worldbody/body[@name='object']")
        geom = body.find('geom')
        if kind == 'soft':
            geom.set('contype', '0'); geom.set('conaffinity', '0')
            geom.set('rgba', '0 0 0 0'); geom.set('size', '.001 .001 .001')
            body.set('gravcomp', '1')
            root.find('option').set('integrator', 'discrete')
            root.find('option').set('solver', 'CG')
            root.find('option').set('timestep', '.001')
            self.config = replace(config, timestep=.001)
            self.young = float(rng.uniform(40000., 70000.))
            flex = ET.SubElement(root.find('worldbody'), 'flexcomp', name='elastic_target',
                                 type='grid', dim='3', dof='trilinear', count='3 3 3',
                                 spacing='.018 .018 .018', pos='.48 0 .026', mass='.05', radius='.001',
                                 rgba='.15 .75 .45 1')
            ET.SubElement(flex, 'elasticity', young=str(self.young), poisson='.3', damping='.005')
            ET.SubElement(flex, 'contact', selfcollide='none', friction='1.2 .01 .001', condim='3')
        elif kind == 'articulated':
            geom.set('size', '.022 .018 .018'); geom.set('mass', '.06')
            lid = ET.SubElement(body, 'body', name='hinged_lid', pos='-.022 0 .023')
            ET.SubElement(lid, 'joint', name='lid_joint', type='hinge', axis='0 1 0',
                          range='-1.2 0', stiffness='.015', springref='-.5', damping='.001')
            ET.SubElement(lid, 'geom', name='lid_geom', type='box', pos='.022 0 0',
                          size='.022 .018 .003', mass='.015', rgba='.9 .6 .15 1', friction='1.2 .01 .001')
        elif kind == 'novel':
            # Each seed creates a new metric solid; no catalog/template is supplied to the observer.
            sx, sy, sz = rng.uniform([.019, .016, .018], [.032, .026, .029])
            shape = ('tapered', 'asymmetric', 'notched', 'wedge')[seed % 4]
            geom.set('mass', '.06')
            if shape == 'notched':
                geom.set('size', f'{sx} {sy*.55} {sz}')
                geom.set('pos', f'0 {-sy*.45} 0')
                ET.SubElement(body, 'geom', name='target_lobe', type='box',
                              size=f'{sx*.45} {sy*.45} {sz}', pos=f'{-sx*.55} {sy*.55} 0',
                              mass='.025', friction='1.2 .01 .001', rgba='.8 .35 .12 1')
            else:
                vertices = corners([sx, sy, sz])
                upper = vertices[:, 2] > 0
                vertices[upper, :2] *= .72 if shape == 'tapered' else .92
                if shape == 'asymmetric':
                    vertices[upper, 0] += .009
                if shape == 'wedge':
                    vertices = np.array([[x, y, z] for y in (-sy, sy)
                                         for x, z in ((-sx, -sz), (sx, -sz), (-sx, sz))])
                ET.SubElement(root.find('asset'), 'mesh', name='held_out_shape',
                              vertex=' '.join(map(str, vertices.ravel())))
                geom.set('type', 'mesh'); geom.attrib.pop('size', None)
                geom.set('mesh', 'held_out_shape')
            self.shape = shape
        elif kind != 'rigid':
            raise ValueError('Unknown research object kind')
        self.model = mujoco.MjModel.from_xml_string(ET.tostring(root, encoding='unicode'))
        self.data = mujoco.MjData(self.model)
        self.object_body = self.model.body('object').id
        self.target_bodies = {self.object_body}
        for bid in range(self.object_body + 1, self.model.nbody):
            parent = bid
            while parent and parent not in self.target_bodies:
                parent = int(self.model.body_parentid[parent])
            if parent in self.target_bodies:
                self.target_bodies.add(bid)
        if kind == 'soft':
            self.node_bodies = self.model.flex_nodebodyid.copy()
            self.target_bodies = set(map(int, self.node_bodies))
            self.node_qpos = np.array([[self.model.jnt_qposadr[self.model.body_jntadr[b] + j]
                                       for j in range(3)] for b in self.node_bodies])
        self.object_geoms = {int(g) for g in range(self.model.ngeom)
                             if self.model.geom_bodyid[g] in self.target_bodies and self.model.geom_contype[g]}
        self.object_model = ObjectModel(kind, corners([.02, .02, .02]),
                                       float(np.sum(self.model.body_mass[list(self.target_bodies)])))
        self.nominal_mass = self.object_model.mass
        self.nominal_body_mass = self.model.body_mass.copy()
        self.nominal_body_inertia = self.model.body_inertia.copy()
        self.object_id = kind
        self._original_contype = self.model.geom_contype.copy()
        self._original_conaffinity = self.model.geom_conaffinity.copy()
        self._original_rgba = self.model.geom_rgba.copy()
        self.material = {'mass_kg': self.nominal_mass, 'friction': 1.2, 'delay_steps': 0}
        # Recompile preserves robot identifiers; verify rather than relying on numeric ordering.
        self.arm_qpos = self.model.jnt_qposadr[self.arm_joints]
        self.arm_dofs = self.model.jnt_dofadr[self.arm_joints]
        self.lid_joint = self.model.joint('lid_joint').id if kind == 'articulated' else None

    def reset(self, rng, fixed=False, object_id=None):
        self.monitoring = False; self.reset_count += 1; self.delay_steps = 0; self._delay.clear()
        mujoco.mj_resetData(self.model, self.data)
        self.model.body_mass[:] = self.nominal_body_mass
        self.model.body_inertia[:] = self.nominal_body_inertia
        if self.domain and self.kind != 'soft':
            mass = float(rng.uniform(.08, .25)); scale = mass / self.nominal_mass
            self.model.body_mass[list(self.target_bodies)] *= scale
            self.model.body_inertia[list(self.target_bodies)] *= scale
        else:
            mass = self.nominal_mass
        self.object_model.mass = mass
        mujoco.mj_setConst(self.model, self.data)
        friction = float(rng.uniform(.30, .85)) if self.domain else 1.2
        for g in range(self.model.ngeom):
            if g in self.object_geoms or self.model.geom_bodyid[g] in self.finger_bodies:
                self.model.geom_friction[g, 0] = friction
        self.data.qpos[self.arm_qpos] = self.config.home
        self.data.qpos[self.finger_qpos] = .04
        self.data.ctrl[self.arm_actuators] = self.config.home
        self.data.ctrl[self.gripper_actuator] = 255
        x = .48 if fixed else rng.uniform(*self.config.spawn_x)
        y = 0. if fixed else rng.uniform(*self.config.spawn_y)
        yaw = 0. if fixed else rng.uniform(-np.pi, np.pi)
        c, s = np.cos(yaw), np.sin(yaw); r = np.array([[c, -s, 0.], [s, c, 0.], [0., 0., 1.]])
        if self.kind == 'soft':
            base = self.model.body_pos[self.node_bodies].copy()
            desired = (base - [.48, 0., .026]) @ r.T + [x, y, .026]
            self.data.qpos[self.node_qpos] = desired - base
            self.data.qpos[self.object_qpos:self.object_qpos+3] = [-5., -5., -5.]
        else:
            self.data.qpos[self.object_qpos:self.object_qpos+3] = [x, y, .04]
            self.data.qpos[self.object_qpos+3:self.object_qpos+7] = [np.cos(yaw/2), 0., 0., np.sin(yaw/2)]
        if self.lid_joint is not None:
            self.data.qpos[self.model.jnt_qposadr[self.lid_joint]] = rng.uniform(-.8, -.3)
        mujoco.mj_forward(self.model, self.data)
        self.step_for(.8)
        self.max_gripper_force = 0.
        self.initial_center = self.target_center().copy()
        self.initial_qpos = self.data.qpos.copy()
        self.initial_vertices = self.collision_vertices().copy()
        self.max_strain = 0.; self.max_contact_force = 0.; self.lid_angles = []
        if self.kind == 'soft':
            edges = self.model.flex_edge
            self.reference_lengths = np.linalg.norm(self.initial_vertices[edges[:, 1]] - self.initial_vertices[edges[:, 0]], axis=1)
        self.delay_steps = int(rng.integers(0, 7)) if self.domain else 0
        self._delay.extend(self.data.ctrl.copy() for _ in range(self.delay_steps))
        self.material = {'mass_kg': mass, 'friction': friction, 'delay_steps': self.delay_steps}
        self.monitoring = True
        if self.recorder:
            self.recorder.reset_time()
        return self.object_pose()

    def step(self):
        requested = self.data.ctrl.copy()
        self._delay.append(requested.copy())
        if len(self._delay) > self.delay_steps:
            self.data.ctrl[:] = self._delay.popleft()
        else:
            self.data.ctrl[:] = self._delay[0]
        super().step()
        self.data.ctrl[:] = requested
        if not self.monitoring:
            return
        forces = self.contact_forces()
        self.max_contact_force = max(self.max_contact_force, max(forces.values(), default=0.))
        if self.kind == 'soft':
            vertices = self.collision_vertices(); edges = self.model.flex_edge
            lengths = np.linalg.norm(vertices[edges[:, 1]]-vertices[edges[:, 0]], axis=1)
            self.max_strain = max(self.max_strain, float(np.max(np.abs(lengths/self.reference_lengths-1))))
        if self.lid_joint is not None:
            self.lid_angles.append(float(self.data.qpos[self.model.jnt_qposadr[self.lid_joint]]))

    def object_pose(self, data=None):
        if getattr(self, 'kind', None) == 'soft' and hasattr(self, 'node_bodies'):
            return transform(np.eye(3), self.target_center(data))
        return super().object_pose(data)

    def target_center(self, data=None):
        data = self.data if data is None else data
        if self.kind == 'soft':
            return data.flexvert_xpos.mean(axis=0)
        bodies = list(self.target_bodies)
        return np.average(data.xipos[bodies], axis=0, weights=self.model.body_mass[bodies])

    def target_velocity(self):
        values = []; bodies = list(self.target_bodies)
        for body in bodies:
            velocity = np.zeros(6)
            mujoco.mj_objectVelocity(self.model, self.data, mujoco.mjtObj.mjOBJ_BODY, body, velocity, 0)
            values.append(velocity[3:])
        return np.average(values, axis=0, weights=self.model.body_mass[bodies])

    def collision_vertices(self, data=None):
        data = self.data if data is None else data
        if self.kind == 'soft' and hasattr(self, 'node_bodies'):
            return data.flexvert_xpos.copy()
        return super().collision_vertices(data)

    def target_contact(self, contact):
        return (self.kind == 'soft' and 0 in contact.flex) or any(int(g) in self.object_geoms for g in contact.geom)

    def other_geom(self, contact):
        if self.kind == 'soft' and 0 in contact.flex:
            return int(contact.geom[1 if contact.flex[0] == 0 else 0])
        return int(contact.geom2 if contact.geom1 in self.object_geoms else contact.geom1)

    def contact_forces(self):
        forces = {body: 0. for body in self.finger_bodies}; wrench = np.zeros(6)
        for index, contact in enumerate(self.data.contact[:self.data.ncon]):
            if self.target_contact(contact):
                other = self.other_geom(contact)
                if other >= 0:
                    body = int(self.model.geom_bodyid[other])
                    if body in forces:
                        mujoco.mj_contactForce(self.model, self.data, index, wrench)
                        forces[body] += max(0., float(wrench[0]))
        return forces

    def finger_contacts(self, data=None):
        data = self.data if data is None else data
        touching = set()
        for contact in data.contact[:data.ncon]:
            if contact.dist <= .001 and self.target_contact(contact):
                other = self.other_geom(contact)
                if other >= 0 and int(self.model.geom_bodyid[other]) in self.finger_bodies:
                    touching.add(int(self.model.geom_bodyid[other]))
        return touching

    def table_contact(self):
        return any(self.target_contact(c) and self.other_geom(c) == self.table_geom and c.dist < .001
                   for c in self.data.contact[:self.data.ncon])
