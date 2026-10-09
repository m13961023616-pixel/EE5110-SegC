"""Bounded active observations, geometric confidence and optional instance masks.

Synthetic sensor generation sees simulation geometry. The point-only estimator
does not. Instance masks are ideal simulation annotations, explicitly logged.
"""
from dataclasses import dataclass
import mujoco
import numpy as np
from .depth_sensing import estimate_box_pose
from .planning import StageFailure


@dataclass(frozen=True)
class ActiveConfig:
    dropout: float = .98
    permanent_dropout: float = .10
    noise_m: float = .0005
    resolution: int = 96
    batch_frames: int = 8
    minimum_frames: int = 16
    maximum_frames: int = 64
    maximum_views: int = 3
    minimum_unique_points: int = 48
    position_stability_m: float = .003
    yaw_stability_rad: float = .08
    extent_error_m: float = .006

    def __post_init__(self):
        if not (0 <= self.dropout <= 1 and 0 <= self.permanent_dropout <= 1 and self.noise_m >= 0):
            raise ValueError('Invalid optical corruption')
        if not (1 <= self.minimum_frames <= self.maximum_frames <= 128 and 1 <= self.maximum_views <= 3 and self.batch_frames > 0):
            raise ValueError('Invalid observation budget')


def capture_view(env, resolution, view, instance_mask=False):
    """Calibrated orthographic rays; target mask is an ideal annotation channel."""
    offset = (np.array([0., 0., .70]), np.array([.35, 0., .70]), np.array([0., -.35, .70]))[view]
    direction = -offset / np.linalg.norm(offset)
    groups = np.array([1, 0, 0, 1, 0, 0], dtype=np.uint8)
    hit = np.zeros(1, dtype=np.int32)
    points = []
    for x in np.linspace(.30, .68, resolution):
        for y in np.linspace(-.22, .12, resolution):
            origin = np.array([x, y, 0.]) + offset
            d = mujoco.mj_ray(env.model, env.data, origin, direction, groups, 1, -1, hit)
            if d >= 0 and (not instance_mask or int(hit[0]) in env.object_geoms):
                points.append(origin + d * direction)
    return np.asarray(points).reshape(-1, 3)


def confidence(points, state, config, previous):
    p = points[(points[:, 2] > .012) & (points[:, 2] < .12)]
    unique = len(np.unique(np.round(p[:, :2], 5), axis=0))
    local = (p - state.pose[:3, 3]) @ state.pose[:3, :3]
    observed = np.ptp(local, axis=0)
    expected = np.ptp(state.vertices, axis=0)
    # Upright roll determines which local axes span the horizontal footprint.
    axes = np.argsort(np.abs(state.pose[2, :3]))[:2]
    extent_error = float(np.max(np.abs(observed[axes] - expected[axes])))
    shift = float('inf') if previous is None else float(np.linalg.norm(state.pose[:3, 3]-previous.pose[:3, 3]))
    yaw = float(np.arctan2(state.pose[1, 0], state.pose[0, 0]))
    old_yaw = yaw if previous is None else float(np.arctan2(previous.pose[1, 0], previous.pose[0, 0]))
    angle = abs((yaw-old_yaw+np.pi/2) % np.pi-np.pi/2)
    accepted = (unique >= config.minimum_unique_points and extent_error <= config.extent_error_m
                and shift <= config.position_stability_m and angle <= config.yaw_stability_rad)
    return {'accepted': bool(accepted), 'unique_points': unique, 'extent_error_m': extent_error,
            'position_change_m': None if not np.isfinite(shift) else shift, 'yaw_change_rad': angle}


class ActiveObserver:
    def __init__(self, config=ActiveConfig(), seed=0, policy='active', instance_mask=False):
        if policy not in ('active', 'fixed'):
            raise ValueError('Unknown observation policy')
        self.config, self.seed, self.policy = config, seed, policy
        self.instance_mask = instance_mask
        self.metrics = {}

    def __call__(self, env):
        cfg = self.config
        rng = np.random.default_rng(self.seed)
        surfaces = []; permanent = []; frames = []; previous = None; history = []; last = None
        self.metrics = {'policy': self.policy, 'segmentation': 'ideal_simulation_instance_mask' if self.instance_mask else 'height_foreground',
                        'checks': history, 'used_frames': 0, 'used_views': 0}
        for index in range(cfg.maximum_frames):
            # Add a viewpoint after each batch, rather than repeatedly measuring occlusion.
            view = min(index // cfg.batch_frames, cfg.maximum_views-1) if self.policy == 'active' else index % cfg.maximum_views
            while len(surfaces) <= view:
                surface = capture_view(env, cfg.resolution, len(surfaces), self.instance_mask)
                surfaces.append(surface)
                permanent.append(rng.random(len(surface)) < cfg.permanent_dropout)
            p = surfaces[view].copy()
            missing = permanent[view] | (rng.random(len(p)) < cfg.dropout)
            p[missing, 2] = 0.
            p[:, 2] += rng.normal(0., cfg.noise_m, len(p))
            frames.append(p)
            used = index+1
            self.metrics.update(used_frames=used, used_views=len(surfaces), nominal_acquisition_s=used/30.)
            if used % cfg.batch_frames and used != cfg.maximum_frames:
                continue
            points = np.concatenate(frames)
            try:
                last = estimate_box_pose(points, env.object_id, env.object_model.vertices)
                check = confidence(points, last, cfg, previous)
                check['frames'] = used; history.append(check)
                previous = last
                if self.policy == 'active' and used >= cfg.minimum_frames and check['accepted']:
                    self.metrics['estimated_pose'] = last.pose.tolist()
                    self.metrics['accepted'] = True
                    return last
            except StageFailure as error:
                history.append({'frames': used, 'accepted': False, 'reason': str(error)})
        if self.policy == 'fixed' and last is not None:
            self.metrics.update(estimated_pose=last.pose.tolist(), accepted=True)
            return last
        self.metrics['accepted'] = False
        raise StageFailure('PERCEPTION_FAIL', 'Observation budget exhausted without geometric confidence')
