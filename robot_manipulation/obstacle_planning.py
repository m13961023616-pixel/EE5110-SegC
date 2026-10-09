"""Collision-checked obstacle transport; physics remains contact driven."""
import numpy as np
from .planning import Planner, StageFailure, Trajectory
from .search import rrt_connect


class ObstaclePlanner(Planner):
    def __init__(self, env, state=None, mode='clearance_rrt', seed=0, stats=None):
        super().__init__(env, state)
        self.mode = mode
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.stats = [] if stats is None else stats

    def spawn(self, state):
        return ObstaclePlanner(self.env, state, self.mode, self.seed, self.stats)

    def trajectory(self, points, target):
        config = self.env.config
        durations = [max(.12, 1.5 * np.max(np.abs(b-a)) / config.max_joint_speed,
                         np.sqrt(6 * np.max(np.abs(b-a)) / config.max_joint_acceleration))
                     for a, b in zip(points[:-1], points[1:])]
        return Trajectory(points, durations, target.copy())

    def search_path(self, target, allow_finger_object=False, attached=False, start_q=None):
        self.prepare()
        start = self.state.qpos[self.env.arm_qpos].copy() if start_q is None else np.asarray(start_q)
        goal = self.ik(target, start)

        def edge_free(a, b):
            try:
                self.validate([a, b], allow_finger_object, attached)
                return True
            except StageFailure:
                return False

        path, stats = rrt_connect(start, goal, self.limits, edge_free, self.rng)
        stats.update(method='rrt_connect', attached=attached, success=path is not None,
                     scope='preview' if self._state is not None else 'execution_plan')
        self.stats.append(stats)
        if path is None:
            raise StageFailure('PLANNING_FAIL', 'RRT-Connect exhausted 180 iterations')
        self.validate(path, allow_finger_object, attached)
        return self.trajectory(path, target)

    def plan(self, target, cartesian=False, allow_finger_object=False, attached=False, start_q=None):
        try:
            return super().plan(target, cartesian, allow_finger_object, attached, start_q)
        except StageFailure as error:
            # Approach/lift/lower keep Cartesian motion; only transit may search.
            if cartesian or error.stage != 'COLLISION_FAIL':
                raise
            return self.search_path(target, allow_finger_object, attached, start_q)

    def plan_transfer(self, target):
        try:
            return super().plan_transfer(target)
        except StageFailure as error:
            if error.stage != 'COLLISION_FAIL':
                raise
        if self.mode == 'clearance_rrt' and self.env.obstacles:
            # Object bottom clears the highest obstacle, plus 60 mm margin.
            top = max(o['center'][2] + o['half_size'][2] for o in self.env.obstacles)
            start_pose = self.env.site_pose(self.state).copy()
            bottom = self.env.collision_vertices(self.state)[:, 2].min()
            height = max(start_pose[2, 3], target[2, 3], start_pose[2, 3] + top + .06 - bottom)
            up, across = start_pose.copy(), target.copy()
            up[2, 3] = across[2, 3] = height
            points = [self.state.qpos[self.env.arm_qpos].copy()]
            try:
                for waypoint in (up, across, target):
                    try:
                        segment = self.plan(waypoint, True, True, True, start_q=points[-1])
                    except StageFailure:
                        segment = self.search_path(waypoint, True, True, start_q=points[-1])
                    points.extend(segment.joints[1:])
                self.validate(points, True, True)
                self.stats.append({'method': 'clearance_route', 'success': True, 'height_m': float(height),
                                   'scope': 'preview' if self._state is not None else 'execution_plan'})
                return self.trajectory(points, target)
            except StageFailure as error:
                self.stats.append({'method': 'clearance_route', 'success': False, 'reason': str(error),
                                   'scope': 'preview' if self._state is not None else 'execution_plan'})
        return self.search_path(target, True, True)
