"""Point-only segmentation/geometry, correlated corruption and no CAD fallback."""
from dataclasses import dataclass
from itertools import product
import hashlib
import numpy as np
from robot_manipulation.active_sensing import capture_view
from robot_manipulation.perception import ObjectState
from robot_manipulation.planning import StageFailure


@dataclass(frozen=True)
class SensorSettings:
    resolution: int = 80
    dropout: float = .35
    noise_m: float = .001
    stripe_fraction: float = .22
    outlier_fraction: float = .04
    calibration_bias_m: float = .002
    frames_per_view: int = 8


def foreground_cluster(points, click=(.48, -.035), voxel=.008):
    """Select a connected foreground component nearest a fixed user workspace hint.

    The hint is fixed before any scene is sampled. No body/geometry identities,
    instance labels, true pose or target-specific template enter this function.
    """
    p = np.asarray(points)
    p = p[np.all(np.isfinite(p), axis=1)]
    p = p[(p[:, 0] > .30) & (p[:, 0] < .68) & (p[:, 1] > -.18) & (p[:, 1] < .11)
          & (p[:, 2] > .009) & (p[:, 2] < .14)]
    if len(p) < 16:
        raise StageFailure('PERCEPTION_FAIL', 'Not enough measured foreground points')
    keys = np.floor(p / voxel).astype(int)
    cells = {}
    for index, key in enumerate(map(tuple, keys)):
        cells.setdefault(key, []).append(index)
    remaining = set(cells); components = []
    neighbors = tuple(product((-1, 0, 1), repeat=3))
    while remaining:
        first = min(remaining); remaining.remove(first); pending = [first]; indices = []
        while pending:
            key = pending.pop(); indices.extend(cells[key])
            for shift in neighbors:
                candidate = tuple(key[i] + shift[i] for i in range(3))
                if candidate in remaining:
                    remaining.remove(candidate); pending.append(candidate)
        if len(indices) >= 16:
            cluster = p[indices]
            distance = np.linalg.norm(np.median(cluster[:, :2], axis=0) - click)
            if distance < .13:
                components.append((distance, cluster))
    if not components:
        raise StageFailure('PERCEPTION_FAIL', 'No point-only cluster near the fixed workspace hint')
    return min(components, key=lambda item: item[0])[1]


def point_state(points, nominal_box=False):
    """Fit measured footprint/yaw without class identity or a stored object mesh."""
    p = foreground_cluster(points)
    best = None
    for yaw in np.linspace(-np.pi/2, np.pi/2, 181, endpoint=False):
        c, s = np.cos(yaw), np.sin(yaw); rotation = np.array([[c, -s], [s, c]])
        local = p[:, :2] @ rotation
        low, high = np.quantile(local, [.01, .99], axis=0)
        area = float(np.prod(high-low))
        if best is None or area < best[0]:
            best = area, rotation, low, high
    _, rotation, low, high = best
    top = float(np.quantile(p[:, 2], .97))
    pose = np.eye(4); pose[:2, :2] = rotation
    pose[:2, 3] = ((low+high)/2) @ rotation.T
    pose[2, 3] = top/2
    # Unknown underside is approximated by the measured support plane z=0.
    vertices = (p-pose[:3, 3]) @ pose[:3, :3]
    if nominal_box:
        vertices = np.array(list(product((-.020, .020), repeat=3)))
    else:
        zlow, zhigh = -top/2, top/2
        vertices = np.vstack([vertices,
            np.array([[x, y, z] for x in ((low-high)[0]/2, (high-low)[0]/2)
                     for y in ((low-high)[1]/2, (high-low)[1]/2) for z in (zlow, zhigh)])])
    return ObjectState('unseen_measured_cluster', pose, np.ptp(vertices, axis=0), vertices)


class PointObserver:
    def __init__(self, seed, method='robust', adverse=False, nominal_box=False):
        self.seed, self.method, self.adverse, self.nominal_box = seed, method, adverse, nominal_box
        self.metrics = {}

    def __call__(self, env):
        cfg = SensorSettings() if self.adverse else SensorSettings(dropout=.12, noise_m=.0005,
                    stripe_fraction=0., outlier_fraction=0., calibration_bias_m=.0005)
        rng = np.random.default_rng(self.seed)
        surfaces = [capture_view(env, cfg.resolution, view, instance_mask=False) for view in range(3)]
        frames = []; counts = []; stripe_offsets = rng.uniform(0, .025, 3)
        bias = rng.uniform(-cfg.calibration_bias_m, cfg.calibration_bias_m, 3)
        correlated = np.zeros(3)
        for frame in range(3*cfg.frames_per_view):
            view = frame % 3
            p = surfaces[view].copy()
            stripe = ((p[:, 0]+stripe_offsets[view]) % .025) < .025*cfg.stripe_fraction
            missing = stripe | (rng.random(len(p)) < cfg.dropout)
            p = p[~missing]
            correlated = .85*correlated + rng.normal(0., cfg.noise_m*.2, 3)
            p += bias+correlated+rng.normal(0., cfg.noise_m, p.shape)
            outliers = rng.random(len(p)) < cfg.outlier_fraction
            p[outliers, 2] += rng.uniform(-.025, .025, int(outliers.sum()))
            frames.append(p); counts.append(len(p))
        # Both methods get the same first frame; corruption is spatially and temporally correlated.
        used = 1 if self.method == 'single' else len(frames)
        points = frames[0] if used == 1 else np.concatenate(frames)
        points = points[(points[:, 2] > .009) & (points[:, 2] < .14)]
        if used > 1 and self.method != 'raw_fusion':
            cells = {}
            for index, frame in enumerate(frames):
                foreground = frame[(frame[:, 2] > .009) & (frame[:, 2] < .14)]
                for point in foreground:
                    key = tuple(np.floor(point/.004).astype(int))
                    samples, seen = cells.setdefault(key, ([], set()))
                    samples.append(point); seen.add(index)
            # Require support in independent packets; repeated outlier points in one
            # packet are not evidence of a persistent physical surface.
            points = np.array([np.median(samples, axis=0) for key, (samples, seen) in sorted(cells.items()) if len(seen) >= 3]).reshape(-1, 3)
        self.metrics = {'source': 'unmasked_range_points', 'segmentation': 'voxel_foreground_connected_components',
                        'template': 'nominal_40mm_box' if self.nominal_box else 'none',
                        'used_frames': used, 'used_views': 1 if used == 1 else 3,
                        'physical_capture_advances_time': False, 'corruption': cfg.__dict__,
                        'first_packet_sha256': hashlib.sha256(frames[0].astype('<f8').tobytes()).hexdigest(),
                        'calibration_bias_m': bias.tolist(), 'returns_per_frame': counts[:used]}
        state = point_state(points, self.nominal_box)
        self.metrics['estimated_pose'] = state.pose.tolist()
        self.metrics['measured_dimensions_m'] = state.dimensions.tolist()
        return state


class GeometryObserver:
    """Oracle geometric control for isolating material/actuator effects, explicitly labeled."""
    def __init__(self):
        self.metrics = {'source': 'simulation_geometry_material_or_control_study', 'used_frames': 0}

    def __call__(self, env):
        pose = env.object_pose()
        vertices = (env.collision_vertices()-pose[:3, 3]) @ pose[:3, :3]
        return ObjectState(env.object_id, pose, np.ptp(vertices, axis=0), vertices)
