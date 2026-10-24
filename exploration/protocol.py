"""Predeclared, bounded coverage of every concrete direction in the CA brief."""
CASES = {
    'crowding_single': dict(topic='crowding', kind='crowding', sensing='single', trials=6),
    'crowding_active': dict(topic='crowding', kind='crowding', sensing='active', trials=6),
    'articulated': dict(topic='articulated', kind='articulated', adaptive=True, trials=6),
    'soft_fixed': dict(topic='deformable', kind='soft', trials=6),
    'soft_adaptive': dict(topic='deformable', kind='soft', adaptive=True, trials=6),
    'novel_prior': dict(topic='novel', kind='novel', sensing='robust', nominal_box=True, trials=12),
    'novel_points': dict(topic='novel', kind='novel', sensing='robust', trials=12),
    'force_fixed': dict(topic='force', kind='rigid', domain=True, trials=12),
    'force_adaptive': dict(topic='force', kind='rigid', domain=True, adaptive=True, trials=12),
    'recovery_single': dict(topic='recovery', kind='rigid', fault=True, trials=6),
    'recovery_retry': dict(topic='recovery', kind='rigid', fault=True, recovery=True, trials=6),
    'sensor_single': dict(topic='sensing', kind='novel', sensing='single', adverse=True, trials=12),
    'sensor_raw_fusion': dict(topic='sensing', kind='novel', sensing='raw_fusion', adverse=True, trials=12),
    'sensor_robust': dict(topic='sensing', kind='novel', sensing='robust', adverse=True, trials=12),
}
PAIRS = [('crowding_single', 'crowding_active'), ('soft_fixed', 'soft_adaptive'),
         ('novel_prior', 'novel_points'), ('force_fixed', 'force_adaptive'),
         ('recovery_single', 'recovery_retry'), ('sensor_single', 'sensor_raw_fusion'),
         ('sensor_raw_fusion', 'sensor_robust')]
GATES = {'lift_m': .08, 'hold_s': 1., 'bilateral_fraction': .95, 'place_m': .055,
         'speed_m_s': .02, 'actuator_force_n': 40., 'soft_edge_strain': .40,
         'neighbor_displacement_m': .02, 'target_penetration_m': .001, 'unsafe_contact_steps': 0}
