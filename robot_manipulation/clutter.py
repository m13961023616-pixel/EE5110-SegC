"""Simultaneously active YCB distractors, compound obstacles and safety evidence."""
import mujoco
import numpy as np
from .environment import Environment
from .dataset import YCB_OBJECTS


def compound_obstacles(height=.22):
    return [
        {'center': [.485, .145, height/2], 'half_size': [.12, .008, height/2]},
        {'center': [.34, .215, .09], 'half_size': [.018, .052, .09]},
        {'center': [.64, .205, .09], 'half_size': [.018, .055, .09]},
    ]


class ClutterEnvironment(Environment):
    def __init__(self, config, distractors=3, **kwargs):
        if distractors not in (0, 3, 5):
            raise ValueError('Supported distractor counts are 0, 3 and 5')
        self.distractor_count = distractors
        self.monitoring = False
        self._clutter_initialized = False
        self.scene_resets = 0
        super().__init__(config, object_names=YCB_OBJECTS, **kwargs)
        self._original_matid = self.model.geom_matid.copy()
        self._clutter_initialized = True
        self.activate_object(self.object_id)
        self.obstacle_geoms = {self.model.geom(f'obstacle_{i}').id for i in range(len(self.obstacles))}

    def activate_object(self, name):
        super().activate_object(name)
        priority = ['tomato_soup_can', 'lemon', 'strawberry', 'gelatin_box', 'pudding_box', 'foam_brick']
        self.distractor_names = [n for n in priority if n != name][:self.distractor_count]
        self.active_names = [name, *self.distractor_names]
        for n in self.active_names:
            body, _, ids = self.object_ids[n]
            self.model.body_gravcomp[body] = 0
            self.model.geom_contype[ids] = self._original_contype[ids]
            self.model.geom_conaffinity[ids] = self._original_conaffinity[ids]
            self.model.geom_rgba[ids] = self._original_rgba[ids]
        if self._clutter_initialized:
            self.model.geom_matid[:] = self._original_matid
            _, _, ids = self.object_ids[name]
            visual = ids[self._original_contype[ids] == 0]
            self.model.geom_matid[visual] = -1
            self.model.geom_rgba[visual] = [.6, .85, .95, .25]

    def _place_initial(self, name, x, y, yaw):
        _, adr, _ = self.object_ids[name]
        roll = np.pi/2 if name == 'gelatin_box' else -np.pi/2 if name == 'pudding_box' else 0.
        c, s = np.cos(roll), np.sin(roll)
        r = np.array([[1,0,0],[0,c,-s],[0,s,c]])
        bottom = (self.objects[name].vertices @ r.T)[:,2].min()
        quat = [np.cos(yaw/2)*np.cos(roll/2),np.cos(yaw/2)*np.sin(roll/2),
                np.sin(yaw/2)*np.sin(roll/2),np.sin(yaw/2)*np.cos(roll/2)]
        self.data.qpos[adr:adr+7] = [x,y,self.config.table_top-bottom+.004,*quat]

    def reset(self, rng, fixed=False, object_id=None):
        self.monitoring = False
        self.scene_resets += 1
        self.activate_object(object_id or self.object_id)
        self.max_gripper_force = 0.
        mujoco.mj_resetData(self.model, self.data)
        if self.recorder:self.recorder.reset_time()
        for _, adr, _ in self.object_ids.values():
            self.data.qpos[adr:adr+7] = [-5,-5,-5,1,0,0,0]
        self.data.qpos[self.arm_qpos] = self.config.home
        self.data.qpos[self.finger_qpos] = .04
        self.data.ctrl[self.arm_actuators] = self.config.home
        self.data.ctrl[self.gripper_actuator] = 255
        x = .48 if fixed else rng.uniform(.43,.52)
        y = -.085 if fixed else rng.uniform(-.105,-.065)
        self._place_initial(self.object_id,x,y,0 if fixed else rng.uniform(-np.pi,np.pi))
        offsets = [(-.105,-.005),(.11,-.015),(.01,.11),(-.115,.105),(.125,.12)]
        for name,(dx,dy) in zip(self.distractor_names,offsets):
            jitter = np.zeros(2) if fixed else rng.uniform(-.004,.004,2)
            self._place_initial(name,x+dx+jitter[0],y+dy+jitter[1],0 if fixed else rng.uniform(-np.pi,np.pi))
        mujoco.mj_forward(self.model,self.data)
        self.step_for(.8)
        self.initial_scene = {n:self.body_pose(n) for n in self.active_names}
        self.initial_distractor_positions = {n:p[:3,3].copy() for n,p in self.initial_scene.items() if n != self.object_id}
        self.maximum_distractor_displacement = 0.
        self.unsafe_contact_steps = 0
        self.maximum_target_penetration = 0.
        self.monitoring = True
        return self.object_pose()

    def body_pose(self,name):
        body,_,_=self.object_ids[name]
        p=np.eye(4);p[:3,:3]=self.data.xmat[body].reshape(3,3);p[:3,3]=self.data.xpos[body]
        return p

    def step(self):
        super().step()
        if not self.monitoring:return
        for name,initial in self.initial_distractor_positions.items():
            distance=float(np.linalg.norm(self.body_pose(name)[:3,3]-initial))
            self.maximum_distractor_displacement=max(self.maximum_distractor_displacement,distance)
        distractor_geoms={int(g) for n in self.distractor_names for g in self.object_ids[n][2]
                          if self._original_contype[g] != 0}
        unsafe=False
        for c in self.data.contact[:self.data.ncon]:
            b1,b2=self.model.geom_bodyid[[c.geom1,c.geom2]]
            robot_other=(b1 in self.robot_bodies and c.geom2 in distractor_geoms) or (b2 in self.robot_bodies and c.geom1 in distractor_geoms)
            unsafe |= bool(robot_other and c.dist < -.0005)
            if c.geom1 in self.object_geoms or c.geom2 in self.object_geoms:
                other=c.geom2 if c.geom1 in self.object_geoms else c.geom1
                if other in distractor_geoms or other in self.obstacle_geoms:
                    self.maximum_target_penetration=max(self.maximum_target_penetration,-float(c.dist))
                    unsafe |= c.dist < -.001
        self.unsafe_contact_steps += int(unsafe)

    def scene_metrics(self):
        return {'distractor_count':self.distractor_count, 'active_objects':list(self.active_names),
                'initial_scene':{n:p.tolist() for n,p in self.initial_scene.items()},
                'distractor_max_displacement_m':self.maximum_distractor_displacement,
                'unsafe_contact_steps':self.unsafe_contact_steps,
                'max_target_penetration_m':self.maximum_target_penetration,
                'scene_resets':self.scene_resets}
