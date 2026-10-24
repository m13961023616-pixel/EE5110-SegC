"""Bounded, mesh-derived alternatives when a vertical grasp hits a neighbor."""
import numpy as np
from .grasp import GraspCandidate
from .robust_obstacles import symmetric_candidates


def local_candidates(state, config):
    """Keep the baseline prefix; add at most 16 checked inclined grasps.

    Rotation about the closing axis preserves required jaw aperture. Small
    offsets along the other horizontal axis move the palm clear of neighbors.
    All geometry comes from the estimated pose/template, not the true pose.
    Feasibility, holding and scene preservation remain independent checks.
    """
    baseline = symmetric_candidates(state, config)
    result = list(baseline)
    vertices = state.vertices @ state.pose[:3, :3].T + state.pose[:3, 3]
    for degrees in (30., -30., 45., -45.):
        for offset in (.012, -.012):
            for candidate in baseline:
                if candidate.pose[2, 2] > -.999:
                    continue
                # Keep the pad center inside the estimated surface footprint.
                axis = candidate.pose[:3, 0]
                support = (vertices - candidate.pose[:3, 3]) @ axis
                if not support.min() + .010 <= offset <= support.max() - .010:
                    continue
                angle = np.deg2rad(degrees)
                c, s = np.cos(angle), np.sin(angle)
                rotation = candidate.pose[:3, :3] @ np.array([[c, 0., s], [0., 1., 0.], [-s, 0., c]])
                width = float(np.ptp(vertices @ rotation[:, 1]) + .006)
                if width > .080:
                    continue
                pose = candidate.pose.copy()
                pose[:3, :3] = rotation
                pose[:3, 3] += offset * axis
                pregrasp, lift = pose.copy(), pose.copy()
                pregrasp[:3, 3] -= rotation[:, 2] * config.pregrasp_clearance
                lift[2, 3] += config.lift_distance
                result.append(GraspCandidate(pose, pregrasp, lift, width, candidate.score))
                if len(result) - len(baseline) == 16:
                    return result
    return result
