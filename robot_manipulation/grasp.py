from dataclasses import dataclass
import numpy as np
from .transforms import transform, top_rotation


@dataclass
class GraspCandidate:
    pose: np.ndarray
    pregrasp: np.ndarray
    lift: np.ndarray
    width: float
    score: float = 0.


def generate_candidates(state, config):
    """Mesh fit with inclined approaches to reach stable sidewall contacts."""
    vertices = state.vertices @ state.pose[:3, :3].T + state.pose[:3, 3]
    low, high = vertices.min(axis=0), vertices.max(axis=0)
    center = (low + high) / 2
    height = high[2] - low[2]
    round_shape = len(state.vertices) > 8 and state.dimensions.max() / state.dimensions.min() < 1.3
    tall_thin = height > .075 and state.dimensions.max() / state.dimensions.min() > 2.
    tilt = np.pi / 2 if tall_thin else np.pi / 4 if round_shape else 0.
    object_yaw = np.arctan2(state.pose[1, 0], state.pose[0, 0])
    candidates = []
    for offset in (0., np.pi / 2, np.pi / 4, -np.pi / 4):
        yaw = (object_yaw + offset + np.pi / 2) % np.pi - np.pi / 2
        for angle in ((tilt, -tilt, 0.) if tilt else (0.,)):
            c, s = np.cos(angle), np.sin(angle)
            rotation = top_rotation(yaw) @ np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
            local = (vertices - center) @ rotation
            width = np.ptp(local[:, 1]) + .006
            if width > .080:
                continue
            point = center.copy()
            point[2] = (max(low[2] + (.055 if tall_thin else .022), low[2] + (.4 if round_shape else .55) * height)
                        if angle else max(low[2] + .017, low[2] + .55 * height, high[2] - .025))
            if tall_thin and angle:
                depth = max(0., np.ptp(local[:, 2]) / 2 - .010)
                point -= rotation[:, 2] * depth
            pose = transform(rotation, point)
            pregrasp, lift = pose.copy(), pose.copy()
            pregrasp[:3, 3] -= rotation[:, 2] * config.pregrasp_clearance
            lift[2, 3] += config.lift_distance
            score = .08 - width + (.02 if angle else 0.)
            candidates.append(GraspCandidate(pose, pregrasp, lift, float(width), float(score)))
    return sorted(candidates, key=lambda candidate: candidate.score, reverse=True)


def generate(state, config):
    candidates = generate_candidates(state, config)
    if not candidates:
        raise ValueError('No mesh-based grasp fits the Panda gripper')
    return candidates[0]
