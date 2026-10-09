"""Audit paired physical execution of synthetic depth sensing methods."""
from pathlib import Path
import sys
import json
from collections import Counter
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from sensing_main import source_hash, OBJECTS
from benchmark_sensing import CASES


def main():
    reference=None;summary={};provenance=None
    for name,(mode,dropout,views) in CASES.items():
        folder=ROOT/'docs/validation/v1.4.0'/name
        logs=list(folder.glob('trials_*.jsonl'));summaries=list(folder.glob('summary_*.json'))
        assert len(logs)==len(summaries)==1
        rows=[json.loads(l) for l in logs[0].read_text().splitlines()];s=json.loads(summaries[0].read_text())
        assert s['source_sha256']==source_hash() and s['code_version']=='1.4.0'
        assert s['seed']==20261501 and len(rows)==s['trials']==60
        assert s['mode']==mode and s['sensor']['dropout']==dropout and s['sensor']['views']==views
        assert s['sensor']['frames']==64 and s['sensor']['noise_m']==.0005
        assert s['sensor']['resolution']==96 and s['sensor']['minimum_points']==24
        versions={k:s[k] for k in ('python','mujoco','numpy','dataset_commit','robot_model_commit')}
        if provenance is None:provenance=versions
        assert versions==provenance
        assert Counter(r['object_id'] for r in rows)=={o:20 for o in OBJECTS}
        assert s['successes']==sum(r['success'] for r in rows)
        assert s['failures']==dict(Counter(r['failure_stage'] for r in rows if not r['success']))
        config=dict(s['config']);config.pop('output_dir')
        assert config['success_height']==.08 and config['place_tolerance']==.055
        assert config['hold_seconds']==1 and config['gripper_force_limit']==40
        if reference is None:reference=rows;reference_config=config
        assert config==reference_config
        for i,(a,r) in enumerate(zip(reference,rows),1):
            assert r['object_id']==a['object_id'] and r['scene_seed']==20262501+i and r['sensor_seed']==20361501+i
            np.testing.assert_array_equal(r['spawn_pose'],a['spawn_pose'])
            assert r['peak_gripper_force_n']<=40+1e-6
            if r['success']:
                assert r['lift_success'] and r['bilateral_contact_fraction']>=.95
                assert r['min_hold_height_m']>r['initial_height_m']+.08
                assert r['released'] and r['place_table_contact'] and r['place_success']
                assert r['place_distance_m']<.055 and r['place_linear_speed_m_s']<.02
                assert r['sensing']['foreground_returns']>=24
                np.testing.assert_array_equal(r['estimated_pose'],r['sensing']['estimated_pose'])
        summary[name]=s['successes'];print(name,s['successes'],'/60',s['failures'])
    assert summary['multiview']>summary['damaged_single']
    print('Verified 240 paired trials with unchanged physics and source fingerprint')


if __name__=='__main__':main()
