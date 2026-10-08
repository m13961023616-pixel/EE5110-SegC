from dataclasses import dataclass
import numpy as np


@dataclass
class ObjectState:
    object_id: str
    pose: np.ndarray
    dimensions: np.ndarray
    vertices: np.ndarray | None = None


def observe(env):
    """Oracle pose: no camera, segmentation or estimated perception in v0."""
    return ObjectState(env.object_id, env.object_pose(), env.object_model.dimensions,
                       env.object_model.vertices)
