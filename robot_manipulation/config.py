from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Config:
    timestep: float = 0.002
    table_top: float = 0.0
    object_size: float = 0.04
    object_mass: float = 0.05
    spawn_x: tuple = (0.40, 0.55)
    spawn_y: tuple = (-0.12, 0.12)
    pregrasp_clearance: float = 0.14
    lift_distance: float = 0.16
    success_height: float = 0.08
    hold_seconds: float = 1.0
    position_tolerance: float = 0.002
    rotation_tolerance: float = 0.025
    tracking_tolerance: float = 0.012
    tracking_rotation_tolerance: float = 0.10
    max_joint_speed: float = 0.5
    max_joint_acceleration: float = 2.0
    place_xy: tuple = (0.48, 0.22)
    place_tolerance: float = 0.055
    place_clearance: float = 0.008
    gripper_stiffness: float = 1000.
    gripper_force_limit: float = 40.
    contact_impratio: float = 10.
    grip_preload: float = 16.
    grip_load_margin: float = 4.
    gravity_compensation: bool = True
    home: tuple = (0.0, -0.4, 0.0, -2.2, 0.0, 1.8, 0.785398)
    output_dir: Path = ROOT / 'outputs'
