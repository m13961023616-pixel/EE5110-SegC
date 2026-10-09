"""Synthetic orthographic range sensing: optical dropout is an explicit model.

Sensor generation may access simulation; estimate_box_pose only accepts measured
points and a known mesh. Poses follow T_world_object. No refractive optics claim.
"""
from dataclasses import dataclass
import mujoco
import numpy as np
from .perception import ObjectState
from .planning import StageFailure


@dataclass(frozen=True)
class DepthConfig:
    dropout: float = .98
    noise_m: float = .0005
    frames: int = 64
    views: int = 2
    resolution: int = 96
    minimum_points: int = 24

    def __post_init__(self):
        if not 0 <= self.dropout <= 1 or self.noise_m < 0 or not 1 <= self.frames <= 64 or self.views not in (1,2) or self.resolution < 16:
            raise ValueError('Invalid bounded depth sensor configuration')


def range_surface(env, resolution, side=False):
    """Calibrated overhead ray grid, all collision surfaces (no semantic mask)."""
    points = []
    groups = np.array([1, 0, 0, 1, 0, 0], dtype=np.uint8)
    direction = np.array([-.35, 0., -.70]) if side else np.array([0., 0., -1.])
    direction /= np.linalg.norm(direction)
    hit = np.zeros(1, dtype=np.int32)
    for x in np.linspace(.32, .63, resolution):
        for y in np.linspace(-.20, .20, resolution):
            origin = np.array([x + (.35 if side else 0.), y, .70])
            distance = mujoco.mj_ray(env.model, env.data, origin, direction, groups, 1, -1, hit)
            if distance >= 0:
                points.append(origin + distance * direction)
    return np.asarray(points)


def measurements(surface, rng, config):
    """Drop foreground returns to the table; non-optical physics is unchanged."""
    frames = []
    for _ in range(config.frames):
        p = surface[_ % len(surface)].copy()
        foreground = p[:, 2] > .012
        missing = foreground & (rng.random(len(p)) < config.dropout)
        p[missing, 2] = 0.
        p[:, 2] += rng.normal(0., config.noise_m, len(p))
        frames.append(p)
    return frames


def estimate_box_pose(points, object_id, vertices, minimum_points=24):
    """Fit an upright known box footprint; no env or true pose argument.

    Scan yaw using minimum-area rectangular support of foreground returns.
    Known template roll and height constrain otherwise unobservable pose axes.
    """
    p = points[(points[:, 2] > .012) & (points[:, 2] < .12)]
    if len(p) < minimum_points:
        raise StageFailure('PERCEPTION_FAIL', f'Only {len(p)} foreground returns; need {minimum_points}')
    roll = np.pi / 2 if object_id == 'gelatin_box' else -np.pi / 2 if object_id == 'pudding_box' else 0.
    c, s = np.cos(roll), np.sin(roll)
    upright = np.array([[1., 0, 0], [0, c, -s], [0, s, c]])
    template = vertices @ upright.T
    bounds = np.array([template.min(axis=0), template.max(axis=0)])
    best = None
    for yaw in np.linspace(-np.pi/2, np.pi/2, 361, endpoint=False):
        c, s = np.cos(yaw), np.sin(yaw)
        r = np.array([[c, -s], [s, c]])
        local = p[:, :2] @ r
        low, high = local.min(axis=0), local.max(axis=0)
        # Known asymmetric dimensions resolve the 90-degree ambiguity.
        width = high - low
        score = float(np.sum((width - (bounds[1,:2]-bounds[0,:2]))**2))
        if best is None or score < best[0]:
            best = score, r, (low+high)/2
    _, r, center = best
    pose = np.eye(4)
    rz = np.eye(3); rz[:2,:2] = r
    pose[:3,:3] = rz @ upright
    pose[:2,3] = (center - (bounds[0,:2]+bounds[1,:2])/2) @ r.T
    # Top returns include sidewalls: upper quantile estimates the top plane.
    pose[2,3] = np.quantile(p[:,2], .85) - bounds[1,2]
    return ObjectState(object_id, pose, np.ptp(vertices, axis=0), vertices.copy())


class DepthObserver:
    def __init__(self, config, seed, mode='fusion'):
        self.config, self.seed, self.mode = config, seed, mode
        self.metrics = {}

    def __call__(self, env):
        surface = [range_surface(env, self.config.resolution)]
        if self.config.views == 2 and self.mode != 'single':
            surface.append(range_surface(env, self.config.resolution, side=True))
        frames = measurements(surface, np.random.default_rng(self.seed), self.config)
        points = frames[0] if self.mode == 'single' else np.concatenate(frames)
        self.metrics = {'foreground_returns': int(np.sum((points[:,2]>.012)&(points[:,2]<.12))),
                        'used_frames': 1 if self.mode == 'single' else self.config.frames,
                        'used_views': len(surface), 'nominal_acquisition_s': (1 if self.mode == 'single' else self.config.frames)/30.}
        state = estimate_box_pose(points, env.object_id, env.object_model.vertices, self.config.minimum_points)
        self.metrics['estimated_pose'] = state.pose.tolist()
        return state


def transparent_appearance(env, alpha=.25):
    """Remove printed visual texture and change alpha only, never contacts."""
    for _, _, ids in env.object_ids.values():
        visual = ids[env.model.geom_contype[ids] == 0]
        env.model.geom_matid[visual] = -1
        env.model.geom_rgba[visual] = [.6, .85, .95, alpha]
        env._original_rgba[visual] = env.model.geom_rgba[visual]
