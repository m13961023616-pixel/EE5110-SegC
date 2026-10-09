"""Audit frozen V2 clutter episodes, every attempt, pairing and physical gates."""
from pathlib import Path
import argparse
from collections import Counter
import hashlib
import json
import subprocess
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from clutter_main import source_hash, TARGETS
from benchmark_v2 import CASES
from robot_manipulation.evaluation import wilson_interval


def historical_hash(ref):
    command=['git','-c','safe.directory='+ROOT.as_posix(),'-C',str(ROOT)]
    listing=subprocess.check_output(command+['ls-tree','-r','--name-only',ref,'robot_manipulation/']).decode().splitlines()
    h=hashlib.sha256()
    for name in ['clutter_main.py',*sorted(p for p in listing if p.endswith('.py'))]:
        h.update(name.encode());h.update(subprocess.check_output(command+['show',ref+':'+name]).replace(b'\r\n',b'\n'))
    return h.hexdigest()


def physical_success(row, initial_height):
    assert row['lift_success'] and row['min_hold_height_m'] > initial_height+.08
    assert row['bilateral_contact_fraction']>=.95
    assert row['place_success'] and row['released'] and row['place_table_contact']
    assert row['place_distance_m']<.055 and row['place_linear_speed_m_s']<.02


def scene_safe(metrics):
    return metrics['unsafe_contact_steps']==0 and metrics['max_target_penetration_m']<=.001 and metrics['distractor_max_displacement_m']<=.02


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder',type=Path,default=ROOT/'docs/validation/v2.0.0')
    p.add_argument('--source-ref')
    a=p.parse_args();expected=historical_hash(a.source_ref) if a.source_ref else source_hash()
    groups={};config=None;versions=None
    for name,(scene,mode,count) in CASES.items():
        folder=a.folder/name;logs=list(folder.glob('trials_*.jsonl'));summaries=list(folder.glob('summary_*.json'))
        assert len(logs)==len(summaries)==1
        rows=[json.loads(l) for l in logs[0].read_text().splitlines()];s=json.loads(summaries[0].read_text())
        assert s['source_sha256']==expected and s['code_version']=='2.0.0'
        assert s['seed']==20261601 and s['scene']==scene and s['mode']==mode
        assert s['trials']==len(rows)==count and s['successes']==sum(r['success'] for r in rows)
        assert s['failures']==dict(Counter(r['failure_stage'] for r in rows if not r['success']))
        assert s['success_rate']==s['successes']/count
        np.testing.assert_allclose(s['success_rate_95pct_interval'],wilson_interval(s['successes'],count),atol=1e-12)
        assert Counter(r['object_id'] for r in rows)=={o:count//3 for o in TARGETS}
        assert s['sensor']['dropout']==.98 and s['sensor']['permanent_dropout']==.10
        assert s['sensor']['maximum_frames']==64 and s['sensor']['maximum_views']==3
        assert s['distractor_displacement_limit_m']==.02
        configuration=dict(s['config']);configuration.pop('output_dir')
        if config is None:config=configuration
        assert config==configuration
        assert config['success_height']==.08 and config['hold_seconds']==1.
        assert config['place_tolerance']==.055 and config['gripper_force_limit']==40.
        assert config['max_joint_speed']==.5 and config['max_joint_acceleration']==2.
        provenance={k:s[k] for k in ('python','numpy','mujoco','robot_model_commit','dataset_commit')}
        if versions is None:versions=provenance
        assert versions==provenance
        assert s['distractor_count']==(5 if scene=='dense' else 3 if scene=='clutter' else 0)
        assert len(s['obstacles'])==(0 if scene=='isolated' else 3)
        for i,r in enumerate(rows,1):
            assert r['trial_id']==i and r['scene_seed']==20262601+i
            assert r['sensor_seed']==20361601+i and r['planner_seed']==20461601+i
            assert r['reset_count']==1 and 1<=r['attempt_count']<=s['maximum_attempts']
            assert len(r['attempts'])==r['attempt_count']
            assert 0<=r['peak_gripper_force_n']<=40+1e-6
            initial=r['scene_metrics']['initial_scene']
            assert len(initial)==s['distractor_count']+1 and r['object_id'] in initial
            np.testing.assert_array_equal(initial[r['object_id']],r['spawn_pose'])
            for n,pose in initial.items():
                assert .20<pose[0][3]<.80 and -.35<pose[1][3]<.35
            assert r['observed_frames']==sum(q['sensing']['used_frames'] for q in r['attempts'])
            for j,q in enumerate(r['attempts']):
                assert q['scene_metrics']['scene_resets']==i
                assert 0<q['sensing']['used_frames']<=(64 if j==0 else 128)
                assert q['sensing']['segmentation']=='ideal_simulation_instance_mask'
                assert 0<=q['peak_gripper_force_n']<=40+1e-6
                if q['success']:physical_success(q,q['spawn_pose'][2][3])
                if q['sensing'].get('estimated_pose') is not None:
                    np.testing.assert_array_equal(q['estimated_pose'],q['sensing']['estimated_pose'])
            first=r['attempts'][0]
            assert r['first_attempt_success']==(first['success'] and scene_safe(first['scene_metrics']))
            if r['success']:
                physical_success(r,r['episode_initial_height_m'])
                assert scene_safe(r['scene_metrics'])
        for o in TARGETS:
            obj=[r for r in rows if r['object_id']==o]
            assert s['per_object'][o]['successes']==sum(r['success'] for r in obj)
        groups[name]=rows
        print(name,s['successes'],'/',count,'first',sum(r['first_attempt_success'] for r in rows),s['failures'])
    reference=groups['fixed_clutter']
    for name in ('active_clutter','recovery_clutter'):
        for x,y in zip(reference,groups[name]):
            assert x['object_id']==y['object_id']
            for obj in x['scene_metrics']['initial_scene']:
                np.testing.assert_allclose(x['scene_metrics']['initial_scene'][obj],y['scene_metrics']['initial_scene'][obj],rtol=0,atol=1e-10)
    assert any(r['success'] for r in groups['dense_recovery'])
    assert all(any(r['success'] and r['object_id']==o for r in groups['recovery_clutter']) for o in TARGETS)
    print('Verified 270 episodes, source fingerprint, exact paired clutter, bounded attempts and neighbor gates')


if __name__=='__main__':main()
