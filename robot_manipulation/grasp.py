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
    """Compute top-grasp tool fit from real mesh extents, with four closing axes."""
    vertices = state.vertices @ state.pose[:3, :3].T + state.pose[:3, 3]
    low, high = vertices.min(axis=0), vertices.max(axis=0)
    center = (low + high) / 2
    object_yaw = np.arctan2(state.pose[1, 0], state.pose[0, 0])
    candidates = []
    for offset in (0., np.pi / 2, np.pi / 4, -np.pi / 4):
        yaw = (object_yaw + offset + np.pi / 2) % np.pi - np.pi / 2
        rotation = top_rotation(yaw)
        local = (vertices - center) @ rotation
        width = np.ptp(local[:, 1]) + .006
        if width > .080:
            continue
        point = center.copy()
        height = high[2] - low[2]
        # Keep the palm above tall packaging while contacting the upper sidewall.
        point[2] = max(low[2] + .017, low[2] + .55 * height, high[2] - .025)
        pose = transform(rotation, point)
        pregrasp, lift = pose.copy(), pose.copy()
        pregrasp[2, 3] = max(high[2] + .12, point[2] + config.pregrasp_clearance)
        lift[2, 3] += config.lift_distance
        candidates.append(GraspCandidate(pose, pregrasp, lift, float(width), float(.08 - width)))
    return sorted(candidates, key=lambda candidate: candidate.score, reverse=True)


def generate(state, config):
    candidates = generate_candidates(state, config)
    if not candidates:
        raise ValueError('No mesh-based grasp fits the Panda gripper')
    return candidates[0]
