"""Convention: T_A_B maps coordinates in frame B into frame A (metres)."""
import numpy as np


def transform(rotation, position):
    result = np.eye(4)
    result[:3, :3] = rotation
    result[:3, 3] = position
    return result


def top_rotation(yaw):
    c, s = np.cos(yaw), np.sin(yaw)
    # Grasp +z points down; +x follows object +x; +y is the closing axis.
    return np.array([[c, s, 0], [s, -c, 0], [0, 0, -1.]])


def rotation_error(target, current):
    # SO(3) logarithm in world coordinates; also handles rotations near pi.
    delta = target @ current.T
    angle = np.arccos(np.clip((np.trace(delta) - 1) / 2, -1, 1))
    skew = np.array([delta[2, 1] - delta[1, 2], delta[0, 2] - delta[2, 0],
                     delta[1, 0] - delta[0, 1]])
    if angle < 1e-6:
        return skew / 2
    if np.pi - angle < 1e-4:
        values, vectors = np.linalg.eigh((delta + np.eye(3)) / 2)
        axis = vectors[:, np.argmax(values)]
        return angle * axis
    return angle / (2 * np.sin(angle)) * skew
