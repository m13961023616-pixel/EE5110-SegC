"""Transparent-appearance target pick/place in physically active YCB clutter."""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
import logging
import platform
from pathlib import Path
import mujoco
import numpy as np
from robot_manipulation.config import Config, ROOT
from robot_manipulation.clutter import ClutterEnvironment, compound_obstacles
from robot_manipulation.active_sensing import ActiveObserver, ActiveConfig
from robot_manipulation.clutter_planning import ClutterPlanner
from robot_manipulation.feedback import FeedbackController
from robot_manipulation.control import Controller
from robot_manipulation.recovery import episode
from robot_manipulation.evaluation import Logger

TARGETS = ('foam_brick','gelatin_box','pudding_box')
SCENES = {'isolated':0,'obstacles':0,'clutter':3,'dense':5}


def source_hash():
    h=hashlib.sha256()
    for p in [ROOT/'clutter_main.py',*sorted((ROOT/'robot_manipulation').glob('*.py'))]:
        h.update(p.relative_to(ROOT).as_posix().encode());h.update(p.read_bytes().replace(b'\r\n',b'\n'))
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--headless',action='store_true')
    p.add_argument('--scene',choices=SCENES,default='clutter')
    p.add_argument('--mode',choices=['fixed','active','recovery'],default='recovery')
    p.add_argument('--object',choices=TARGETS)
    p.add_argument('--trials',type=int,default=3)
    p.add_argument('--seed',type=int,default=43)
    p.add_argument('--height',type=float,default=.22)
    p.add_argument('--dropout',type=float,default=.98)
    p.add_argument('--permanent-dropout',type=float,default=.10)
    p.add_argument('--output',type=Path,default=ROOT/'outputs/clutter')
    p.add_argument('--video',type=Path)
    p.add_argument('--snapshot',action='store_true')
    p.add_argument('--require-all-success',action='store_true')
    a=p.parse_args()
    if a.trials<1 or not .12 <= a.height <= .28:p.error('Positive trials and bounded obstacle height required')
    sensor=ActiveConfig(dropout=a.dropout,permanent_dropout=a.permanent_dropout)
    config=Config(spawn_x=(.43,.52),spawn_y=(-.105,-.065),place_xy=(.48,.30),output_dir=a.output)
    obstacles=[] if a.scene=='isolated' else compound_obstacles(a.height)
    roster=[a.object] if a.object else list(TARGETS)
    rng=np.random.default_rng(a.seed);scenes=[]
    while len(scenes)<a.trials:scenes.extend(str(n) for n in rng.permutation(roster))
    meta={'code_version':'2.0.0','scope':'known_box_transparent_proxy_ideal_instance_mask_physical_clutter',
          'source_sha256':source_hash(),'seed':a.seed,'mode':a.mode,'scene':a.scene,'obstacles':obstacles,
          'sensor':asdict(sensor),'object_pool':roster,'distractor_count':SCENES[a.scene],
          'config':{k:str(v) if isinstance(v,Path) else v for k,v in asdict(config).items()},
          'maximum_attempts':2 if a.mode=='recovery' else 1,'distractor_displacement_limit_m':.02,
          'python':platform.python_version(),'numpy':np.__version__,'mujoco':mujoco.__version__,
          'dataset_commit':json.loads((ROOT/'assets/ycb.lock.json').read_text())['commit'],
          'robot_model_commit':json.loads((ROOT/'assets/panda/manifest.json').read_text())['commit']}
    log=Logger(a.output,meta);logging.basicConfig(level=logging.INFO)
    env=ClutterEnvironment(config,distractors=SCENES[a.scene],obstacles=obstacles,gui=not a.headless,realtime=False)
    if a.video:
        from robot_manipulation.video import Recorder
        env.recorder=Recorder(env,a.video)
        env.recorder.title='EE5110 v2.0 | Transparent proxy + physical clutter'
    try:
        for i,name in enumerate(scenes[:a.trials],1):
            scene_seed=a.seed+1000+i; sensor_seed=a.seed+100000+i; planner_seed=a.seed+200000+i
            planner=ClutterPlanner(env,seed=planner_seed)
            controller=FeedbackController(env,planner) if a.mode=='recovery' else Controller(env,planner)
            def factory(index):
                settings=replace(sensor,maximum_frames=128) if index else sensor
                return ActiveObserver(settings,seed=sensor_seed+index*1000000,
                                      policy='fixed' if a.mode=='fixed' else 'active',instance_mask=True)
            before_resets=env.scene_resets
            row=episode(env,planner,controller,np.random.default_rng(scene_seed),i,name,factory,meta['maximum_attempts'])
            row.update(scene_seed=scene_seed,sensor_seed=sensor_seed,planner_seed=planner_seed,
                       scene_metrics=env.scene_metrics(),reset_count=env.scene_resets-before_resets,
                       planner_stats=planner.stats,feedback=getattr(controller,'metrics',{}))
            def scene_safe(metrics):
                return metrics['distractor_max_displacement_m']<=.02 and metrics['unsafe_contact_steps']==0 and metrics['max_target_penetration_m']<=.001
            row['first_attempt_success']=row['attempts'][0]['success'] and scene_safe(row['attempts'][0]['scene_metrics'])
            if row['success'] and not scene_safe(row['scene_metrics']):
                row.update(success=False,failure_stage='CLUTTER_DISTURBANCE_FAIL',reason='Scene safety/neighbor displacement gate failed')
            if row['sensing'].get('estimated_pose'):
                row['pose_translation_error_m']=float(np.linalg.norm(np.array(row['sensing']['estimated_pose'])[:3,3]-np.array(row['attempts'][-1]['spawn_pose'])[:3,3]))
            log.append(row)
        if a.snapshot:
            from robot_manipulation.visualization import save_snapshot
            save_snapshot(env,log.summary_path.with_suffix('.png'))
    finally:
        env.close();s=log.finish()
        print(f"{a.scene}/{a.mode}: {s['successes']}/{s['trials']} {s['failures']}; {log.summary_path}")
    return 1 if a.require_all_success and s['successes']!=a.trials else 0


if __name__=='__main__':raise SystemExit(main())
