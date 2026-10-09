"""Gripper symmetry, alternative transit corridors and safer placement centres."""
import numpy as np
import mujoco
from .grasp import generate_candidates, GraspCandidate
from .obstacle_planning import ObstaclePlanner
from .planning import StageFailure


def symmetric_candidates(state, config):
    result = []
    base = generate_candidates(state, config)
    for candidate in base:
        result.append(candidate)
        # Swap equivalent parallel jaws without changing approach or grasp point.
        poses = [pose.copy() for pose in (candidate.pose, candidate.pregrasp, candidate.lift)]
        for pose in poses:
            pose[:3, :3] = pose[:3, :3] @ np.diag([-1., -1., 1.])
        result.append(GraspCandidate(*poses, candidate.width, candidate.score))
    return result


class RobustObstaclePlanner(ObstaclePlanner):
    def __init__(self, env, state=None, mode='robust', seed=0, stats=None):
        super().__init__(env, state, mode, seed, stats)

    def spawn(self, state):
        return RobustObstaclePlanner(self.env, state, self.mode, self.seed, self.stats)

    def ik(self, target, seed):
        seeds = [np.asarray(seed).copy()]
        for joint, delta in ((2, .7), (2, -.7), (2, 1.4), (2, -1.4), (0, .7), (0, -.7), (4, .7), (4, -.7)):
            alternative = np.asarray(seed).copy()
            alternative[joint] += delta
            seeds.append(np.clip(alternative, self.limits[:, 0] + .005, self.limits[:, 1] - .005))
        for index, alternative in enumerate(seeds):
            try:
                q = super().ik(target, alternative)
                # Reject a converged end pose whose elbow/wrist intersects the workcell.
                # Held-object geometry is checked by validate(), not this IK filter.
                blocked = False
                for c in self.scratch.contact[:self.scratch.ncon]:
                    if c.dist >= -.0005 or c.geom1 in self.env.object_geoms or c.geom2 in self.env.object_geoms:
                        continue
                    b1, b2 = self.env.model.geom_bodyid[[c.geom1, c.geom2]]
                    if b1 in self.env.robot_bodies or b2 in self.env.robot_bodies:
                        robot = b1 if b1 in self.env.robot_bodies else b2
                        other = c.geom2 if b1 in self.env.robot_bodies else c.geom1
                        if other == self.env.floor_geom and robot == self.env.model.body('link0').id:
                            continue
                        blocked = True
                        break
                if not blocked:
                    if index:
                        self.stats.append({'method': 'ik_reseed', 'success': True, 'seed_index': index,
                                           'scope': 'preview' if self._state is not None else 'execution_plan'})
                    return q
            except StageFailure:
                pass
        self.stats.append({'method': 'ik_reseed', 'success': False, 'seeds': len(seeds),
                           'scope': 'preview' if self._state is not None else 'execution_plan'})
        raise StageFailure('IK_FAIL', 'All nine IK seeds fail convergence or static collision checks')

    def plan_transfer(self, target):
        try:
            # Existing orientation-preserving top corridor is still the first choice.
            saved = self.mode
            self.mode = 'clearance_rrt'
            return super().plan_transfer(target)
        except StageFailure:
            pass
        finally:
            self.mode = saved
        start = self.env.site_pose(self.state).copy()
        obstacles = self.env.obstacles
        if not obstacles:
            raise StageFailure('PLANNING_FAIL', 'No obstacle corridor available')
        left = min(o['center'][0] - o['half_size'][0] for o in obstacles) - .10
        right = max(o['center'][0] + o['half_size'][0] for o in obstacles) + .10
        for side in (left, right):
            before, after = start.copy(), target.copy()
            before[0, 3] = after[0, 3] = side
            points = [self.state.qpos[self.env.arm_qpos].copy()]
            try:
                for waypoint in (before, after, target):
                    segment = self.plan(waypoint, True, True, True, start_q=points[-1])
                    points.extend(segment.joints[1:])
                self.validate(points, True, True)
                self.stats.append({'method': 'side_corridor', 'success': True, 'side_x': side})
                return self.trajectory(points, target)
            except StageFailure as error:
                self.stats.append({'method': 'side_corridor', 'success': False, 'side_x': side, 'reason': str(error)})
        raise StageFailure('PLANNING_FAIL', 'Top and both side corridors rejected')

    def plan_placement(self):
        env = self.env
        site, obj = env.site_pose(self.state), env.object_pose(self.state)
        relative = np.linalg.inv(site) @ obj
        local = (env.collision_vertices(self.state) - obj[:3, 3]) @ obj[:3, :3]
        rejected = []
        # All centres stay inside the original 55 mm acceptance zone.
        offsets = ((0., -.025), (0., 0.), (-.02, -.025), (.02, -.025),
                   (-.02, 0.), (.02, 0.), (0., .02))
        for offset in offsets:
            target = site.copy()
            center = np.asarray(env.config.place_xy) + offset
            target[:2, 3] += center - obj[:2, 3]
            try:
                transfer = self.plan_transfer(target)
                self.prepare()
                self.scratch.qpos[env.arm_qpos] = transfer.joints[-1]
                mujoco.mj_forward(env.model, self.scratch)
                future_site = env.site_pose(self.scratch).copy()
                future_object = future_site @ relative
                world = local @ future_object[:3, :3].T + future_object[:3, 3]
                lower = future_site.copy()
                lower[2, 3] -= world[:, 2].min() - env.config.table_top - env.config.place_clearance
                self.plan(lower, True, True, True, start_q=transfer.joints[-1])
                return transfer, center, rejected
            except StageFailure as error:
                rejected.append({'center': center.tolist(), 'stage': error.stage, 'reason': str(error)})
        raise StageFailure('PLACE_PLANNING_FAIL', f'No robust transfer/lower pair: {rejected}')
