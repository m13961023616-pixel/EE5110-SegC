from dataclasses import dataclass
import numpy as np
from .transforms import transform, top_rotation


@dataclass
class GraspCandidate:
    pose: np.ndarray
    pregrasp: np.ndarray
    lift: np.ndarray
    width: float


def generate(state, config):
    yaw = np.arctan2(state.pose[1, 0], state.pose[0, 0])
    yaw = (yaw + np.pi / 2) % np.pi - np.pi / 2  # Parallel jaws have pi symmetry.
    width = float(state.dimensions[1]) + .016
    if width > .08:
        raise ValueError('Object does not fit Panda gripper')
    grasp = transform(top_rotation(yaw), state.pose[:3, 3])
    pregrasp = grasp.copy()
    pregrasp[2, 3] += config.pregrasp_clearance
    lift = grasp.copy()
    lift[2, 3] += config.lift_distance
    return GraspCandidate(grasp, pregrasp, lift, width)
