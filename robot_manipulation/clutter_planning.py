"""Placement orientation choices for compound obstacles, fully edge checked."""
import mujoco
import numpy as np
from .robust_obstacles import RobustObstaclePlanner
from .planning import StageFailure, Planner


class ClutterPlanner(RobustObstaclePlanner):
    def spawn(self, state):
        return ClutterPlanner(self.env, state, self.mode, self.seed, self.stats)

    def plan_transfer(self, target):
        try:
            return Planner.plan_transfer(self, target)
        except StageFailure:
            pass
        if not self.env.obstacles:
            return self.search_path(target, True, True)
        start=self.env.site_pose(self.state).copy()
        top=max(o['center'][2]+o['half_size'][2] for o in self.env.obstacles)
        bottom=self.env.collision_vertices(self.state)[:,2].min()
        height=max(start[2,3],target[2,3],start[2,3]+top+.06-bottom)
        up,across=start.copy(),target.copy()
        up[2,3]=across[2,3]=height
        routes=[('compound_clearance',[up,across,target])]
        for margin in (.045,.075):
            sides=(min(o['center'][0]-o['half_size'][0] for o in self.env.obstacles)-margin,
                   max(o['center'][0]+o['half_size'][0] for o in self.env.obstacles)+margin)
            for side in sides:
                before,after=start.copy(),target.copy()
                before[0,3]=after[0,3]=side
                routes.append(('compound_side',[before,after,target]))
        for method,waypoints in routes:
            points=[self.state.qpos[self.env.arm_qpos].copy()]
            try:
                for waypoint in waypoints:
                    try:
                        segment=self.plan(waypoint,True,True,True,start_q=points[-1])
                    except StageFailure:
                        segment=self.search_path(waypoint,True,True,start_q=points[-1])
                    points.extend(segment.joints[1:])
                self.validate(points,True,True)
                self.stats.append({'method':method,'success':True,'height_m':float(height)})
                return self.trajectory(points,target)
            except StageFailure as error:
                self.stats.append({'method':method,'success':False,'reason':str(error)})
        raise StageFailure('PLANNING_FAIL','All compound corridors rejected')

    def plan_placement(self):
        env=self.env
        site,obj=env.site_pose(self.state),env.object_pose(self.state)
        relative=np.linalg.inv(site)@obj
        local=(env.collision_vertices(self.state)-obj[:3,3])@obj[:3,:3]
        rejected=[]
        for offset in ((0.,-.025),(-.02,-.025),(.02,-.025),(0.,0.)):
            center=np.asarray(env.config.place_xy)+offset
            for angle in (0.,np.pi/4,-np.pi/4,np.pi/2):
                c,s=np.cos(angle),np.sin(angle)
                rz=np.array([[c,-s,0],[s,c,0],[0,0,1.]])
                target=site.copy();target[:3,:3]=rz@site[:3,:3]
                desired=obj[:3,3].copy();desired[:2]=center
                target[:3,3]=desired-target[:3,:3]@relative[:3,3]
                try:
                    transfer=self.plan_transfer(target)
                    self.prepare();self.scratch.qpos[env.arm_qpos]=transfer.joints[-1]
                    mujoco.mj_forward(env.model,self.scratch)
                    future=env.site_pose(self.scratch).copy();future_object=future@relative
                    world=local@future_object[:3,:3].T+future_object[:3,3]
                    lower=future.copy();lower[2,3]-=world[:,2].min()-env.config.table_top-env.config.place_clearance
                    self.plan(lower,True,True,True,start_q=transfer.joints[-1])
                    self.stats.append({'method':'placement_orientation','yaw_delta_rad':angle,'success':True,
                                       'scope':'preview' if self._state is not None else 'execution_plan'})
                    return transfer,center,rejected
                except StageFailure as error:
                    rejected.append({'center':center.tolist(),'yaw_delta_rad':angle,'stage':error.stage,'reason':str(error)})
        raise StageFailure('PLACE_PLANNING_FAIL',f'Compound-obstacle placements rejected: {rejected}')
