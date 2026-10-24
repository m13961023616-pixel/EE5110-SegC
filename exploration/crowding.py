"""Touching/narrow-gap physical clutter and an opaque camera-side occluder."""
import numpy as np
from robot_manipulation.clutter import ClutterEnvironment, compound_obstacles
from robot_manipulation.active_sensing import capture_view


class CrowdedEnvironment(ClutterEnvironment):
    def __init__(self, config, **kwargs):
        self.target_initial_xy = None
        self.layout_scale = .76
        obstacles = compound_obstacles()
        obstacles.append({'center': [.695, -.075, .30], 'half_size': [.006, .16, .30]})
        super().__init__(config, distractors=5, obstacles=obstacles, **kwargs)

    def _place_initial(self, name, x, y, yaw):
        if name == self.object_id:
            self.target_initial_xy = np.array([x, y])
        else:
            x, y = self.target_initial_xy + self.layout_scale*(np.array([x, y])-self.target_initial_xy)
        super()._place_initial(name, x, y, yaw)

    def visibility(self):
        full = [len(capture_view(self, 64, view, True)) for view in range(3)]
        original = self.model.geom_group.copy()
        excluded = set(range(self.model.ngeom))-self.object_geoms
        try:
            self.model.geom_group[list(excluded)] = 4
            clear = [len(capture_view(self, 64, view, True)) for view in range(3)]
        finally:
            self.model.geom_group[:] = original
        return {'visible_returns': full, 'unoccluded_reference_returns': clear,
                'visible_fraction_per_view': [a/b if b else 0. for a, b in zip(full, clear)],
                'evaluation_only_instance_labels': True, 'layout_scale': self.layout_scale,
                'opaque_physical_occluder': True,
                'reference_removes_all_non_target_geometry_including_robot': True}
