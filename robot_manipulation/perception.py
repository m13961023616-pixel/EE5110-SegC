from dataclasses import dataclass
import numpy as np


@dataclass
class ObjectState:
    object_id: str
    pose: np.ndarray
    dimensions: np.ndarray
    vertices: np.ndarray | None = None


def observe(env):
    """Oracle pose with known collision mesh; visual dimensions remain unscaled."""
    pose = env.object_pose()
    vertices = (env.collision_vertices() - pose[:3, 3]) @ pose[:3, :3]
    return ObjectState(env.object_id, pose, env.object_model.dimensions, vertices)
