"""Audit every exploratory episode, paired state, mechanism and physical gate."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
from statistics import mean
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from exploration.protocol import CASES, PAIRS, GATES
from exploration.provenance import source_hash
from robot_manipulation.evaluation import wilson_interval


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def load_case(folder):
    summaries, logs = list(folder.glob('summary_*.json')), list(folder.glob('trials_*.jsonl'))
    require(len(summaries)==len(logs)==1,'Require exactly one complete run: '+str(folder))
    return json.loads(summaries[0].read_text(encoding='utf-8')), [json.loads(l) for l in logs[0].read_text(encoding='utf-8').splitlines()]


def audit(folder):
    protocol = json.loads((folder/'protocol.json').read_text(encoding='utf-8'))
    require(protocol['completed'],'Incomplete study')
    require(protocol['cases']==CASES and protocol['gates']==GATES and protocol['pairs']==[list(p) for p in PAIRS],'Changed protocol')
    frozen = source_hash(); require(protocol['source_sha256']==frozen,'Source fingerprint mismatch')
    require(protocol['seed'] not in protocol['development_seeds'],'Development seed used as held-out evaluation')
    groups = {}; stats = {}; provenance = None
    for name, case in CASES.items():
        summary, rows = load_case(folder/name)
        require(summary['source_sha256']==frozen and summary['version']=='3.0.0','Incorrect source/version')
        require(summary['case']==name and summary['case_definition']==case and summary['seed']==protocol['seed'],'Incorrect condition')
        require(summary['trials']==len(rows)==case['trials'],'Incomplete sample')
        require(summary['successes']==sum(r['success'] for r in rows),'Wrong success count')
        require(summary['first_successes']==sum(r['first_attempt_success'] for r in rows),'Wrong first-attempt count')
        require(summary['failures']==dict(Counter(r['failure_stage'] for r in rows if not r['success'])),'Omitted failure')
        np.testing.assert_allclose(summary['success_rate_95pct_interval'],wilson_interval(summary['successes'],len(rows)),atol=1e-12)
        version = {k:summary[k] for k in ('python','mujoco','numpy','robot_model_commit','dataset_commit')}
        if provenance is None: provenance = version
        require(version==provenance,'Mixed dependency/asset versions')
        for index,row in enumerate(rows,1):
            require(row['source_sha256']==frozen and row['case']==name,'Row/source mismatch')
            require(row['trial_id']==index and row['scene_seed']==protocol['seed']+1000+index
                    and row['sensor_seed']==protocol['seed']+100000+index,'Wrong trial/seed')
            require(row['reset_count']==1 and row['object_robot_welds']==0,'Scene reset or welded grasp')
            require(row['attempt_count']==len(row['attempts']) and 1<=row['attempt_count']<=(2 if case.get('recovery') else 1),'Attempt budget')
            require(0<=row['peak_actuator_force_n']<=40+1e-6,'Force limit exceeded')
            require(row['config']['success_height']==.08 and row['config']['hold_seconds']==1.
                    and row['config']['place_tolerance']==.055 and row['config']['gripper_force_limit']==40.,'Relaxed gates')
            if row['success']:
                require(row['failure_stage']=='SUCCESS','Incorrect success label')
                height = row.get('reference_height_m',row.get('episode_initial_height_m'))
                require(row['min_hold_height_m']>height+.08 and row['bilateral_contact_fraction']>=.95,'Lift/hold gate')
                if case['kind']=='crowding':
                    require(row['released'] and row['place_table_contact'] and row['place_distance_m']<.055
                            and row['place_linear_speed_m_s']<.02,'Invalid physical place')
                    m=row['scene_metrics'];require(m['unsafe_contact_steps']==0 and m['distractor_max_displacement_m']<=.02
                            and m['max_target_penetration_m']<=.001,'Crowding preservation gate')
                else:
                    require(row['released'] and row['table_contact'] and row['place_distance_m']<.055
                            and row['final_speed_m_s']<.02,'Invalid physical place')
            else:
                require(row['failure_stage']!='SUCCESS','Misreported failure')
            if case['kind']=='soft':
                require(row['physical_model']=='Saint_Venant_Kirchhoff_trilinear_flex'
                        and row['flex_vertices']==27 and row['elastic_node_dofs']==24,'Rigid placeholder used for deformable study')
                require(40000<=row['young_modulus_pa']<=70000 and row['max_edge_strain']>=0,'Unreported elastic material')
                if row['success']:require(row['max_edge_strain']<=.40,'Deformation limit exceeded')
            if case['kind']=='novel':
                sensing=row['attempts'][0]['sensing']
                require(sensing['source']=='unmasked_range_points' and sensing['segmentation']=='voxel_foreground_connected_components','Oracle instance segmentation')
                require(sensing['template']==('nominal_40mm_box' if case.get('nominal_box') else 'none'),'Unreported template')
                require(row['asset_seed']==protocol['seed']+300000+index,'Shape seed mismatch')
                require(row['shape_family'] in ('tapered','asymmetric','notched','wedge'),'Missing irregular family')
            if case.get('domain'):
                require(.08<=row['material']['mass_kg']<=.25 and .30<=row['material']['friction']<=.85
                        and 0<=row['material']['delay_steps']<=6,'Unreported domain randomization')
            if case.get('fault'):
                require(row['controller']['injected_partial_closures']==1,'Fault condition not executed physically')
                first=row['attempts'][0]
                require(not first['success'] and first['failure_stage']=='GRASP_FAIL'
                        and 'APPROACH' in first['executed_stages'] and first['closing_contacts']<2,'No actual grasp-failure evidence')
                if row['success']:
                    require(row['attempt_count']==2 and row['recovery_actions']==['checked_open_withdraw_home_reobserve'],'Recovery not demonstrated')
            if case['kind']=='crowding':
                require(row['scene_metrics']['distractor_count']==5 and len(row['scene_metrics']['active_objects'])==6,'Not simultaneous dense clutter')
                require(min(row['visibility']['visible_fraction_per_view'])<.5,'Declared heavy occlusion not observed')
        require(math.isclose(summary['mean_total_time_s'],mean(r['total_time_s'] for r in rows),abs_tol=1e-10),'Wrong timing')
        groups[name]=rows
        stats[name]={**summary,'mean_max_strain':mean(r['max_edge_strain'] for r in rows),
                     'failure_trials':[r['trial_id'] for r in rows if not r['success']],
                     'mean_max_normal_force_n':mean(r.get('max_finger_normal_force_n',0.) for r in rows),
                     'mean_hinge_excursion_rad':mean(r['hinge_excursion_rad'] for r in rows)}
        print(name,summary['successes'],'/',len(rows),summary['failures'])
    paired={}
    for before,after in PAIRS:
        a,b=groups[before],groups[after]
        require(len(a)==len(b),'Unequal paired sample counts')
        for x,y in zip(a,b):
            require(x['pairing_state']==y['pairing_state'] and x['material']==y['material'],'Unpaired initial physics')
            require(x.get('asset_seed')==y.get('asset_seed'),'Unpaired object instance')
            sx=x['attempts'][0]['sensing'];sy=y['attempts'][0]['sensing']
            if 'first_packet_sha256' in sx:
                require(sx['first_packet_sha256']==sy['first_packet_sha256'],'Unpaired corrupted input packet')
        recovered=[x['trial_id'] for x,y in zip(a,b) if not x['success'] and y['success']]
        regressed=[x['trial_id'] for x,y in zip(a,b) if x['success'] and not y['success']]
        n=len(recovered)+len(regressed)
        p=min(1.,2*sum(math.comb(n,k) for k in range(min(len(recovered),len(regressed))+1))/2**n) if n else 1.
        paired[before+'__'+after]={'recovered':recovered,'regressed':regressed,'exact_mcnemar_p':p}
    require(any(r['success'] and r['max_edge_strain']>.005 for r in groups['soft_adaptive']),'No actual deforming grasp success')
    require(any(r['success'] and r['hinge_excursion_rad']>.02 for r in groups['articulated']),'No passive articulation evidence')
    require(any(r['success'] for r in groups['novel_points']),'No template-free held-out success')
    require(any(r['success'] for r in groups['recovery_retry']),'No physical recovery success')
    result={'version':'3.0.0','source_sha256':frozen,'seed':protocol['seed'],'episodes':sum(len(r) for r in groups.values()),
            'groups':stats,'paired':paired,'provenance':provenance,
            'scope':protocol['scope']}
    (folder/'comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Verified',result['episodes'],'episodes across all concrete CA directions; paired physics and mechanism gates')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder',type=Path,default=ROOT/'docs/validation/v3.0.0')
    audit(p.parse_args().folder)


if __name__=='__main__':main()
