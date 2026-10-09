"""Transparent-appearance YCB boxes with explicit synthetic depth dropout."""
import argparse
from dataclasses import asdict
import hashlib
import json
import logging
import platform
from pathlib import Path
import mujoco
import numpy as np
from robot_manipulation.config import Config, ROOT
from robot_manipulation.environment import Environment
from robot_manipulation.depth_sensing import DepthConfig, DepthObserver, transparent_appearance
from robot_manipulation.planning import Planner
from robot_manipulation.control import Controller
from robot_manipulation.pipeline import trial
from robot_manipulation.evaluation import Logger

OBJECTS = ('foam_brick', 'gelatin_box', 'pudding_box')


def source_hash():
    h = hashlib.sha256()
    for p in [ROOT/'sensing_main.py', *sorted((ROOT/'robot_manipulation').glob('*.py'))]:
        h.update(p.relative_to(ROOT).as_posix().encode()); h.update(p.read_bytes().replace(b'\r\n',b'\n'))
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--headless', action='store_true')
    p.add_argument('--mode', choices=['single','fusion'], default='fusion')
    p.add_argument('--dropout', type=float, default=.98)
    p.add_argument('--frames', type=int, default=64)
    p.add_argument('--views', type=int, choices=[1,2], default=2)
    p.add_argument('--trials', type=int, default=3)
    p.add_argument('--seed', type=int, default=43)
    p.add_argument('--object', choices=OBJECTS)
    p.add_argument('--output', type=Path, default=ROOT/'outputs/sensing')
    p.add_argument('--video', type=Path)
    a=p.parse_args()
    if a.trials < 1: p.error('Positive trials required')
    sensor=DepthConfig(dropout=a.dropout, frames=a.frames, views=a.views)
    config=Config(output_dir=a.output)
    roster=[a.object] if a.object else list(OBJECTS)
    random=np.random.default_rng(a.seed); scenes=[]
    while len(scenes)<a.trials: scenes.extend(random.permutation(roster))
    log=Logger(a.output, {'code_version':'2.0.0', 'scope':'synthetic_depth_dropout_known_upright_YCB_boxes',
        'source_sha256':source_hash(), 'seed':a.seed,'mode':a.mode,'sensor':asdict(sensor),
        'config':{k:str(v) if isinstance(v,Path) else v for k,v in asdict(config).items()},
        'object_pool':roster, 'python':platform.python_version(),'mujoco':mujoco.__version__,'numpy':np.__version__,
        'dataset_commit':json.loads((ROOT/'assets/ycb.lock.json').read_text())['commit'],
        'robot_model_commit':json.loads((ROOT/'assets/panda/manifest.json').read_text())['commit']})
    logging.basicConfig(level=logging.INFO)
    env=Environment(config,gui=not a.headless,realtime=False,object_names=roster)
    transparent_appearance(env)
    if a.video:
        from robot_manipulation.video import Recorder
        env.recorder=Recorder(env,a.video)
    planner=Planner(env)
    try:
        for i,name in enumerate(scenes[:a.trials],1):
            observer=DepthObserver(sensor,a.seed+100000+i,a.mode)
            row=trial(env,planner,Controller(env,planner),np.random.default_rng(a.seed+1000+i),i,
                      object_id=str(name),task='place',observer=observer)
            # Ground truth is recorded AFTER estimating solely for evaluation.
            row.update(scene_seed=a.seed+1000+i,sensor_seed=a.seed+100000+i,sensing=observer.metrics)
            if 'estimated_pose' in observer.metrics:
                estimate=np.asarray(observer.metrics['estimated_pose']); truth=np.asarray(row['spawn_pose'])
                row['pose_translation_error_m']=float(np.linalg.norm(estimate[:3,3]-truth[:3,3]))
            log.append(row)
    finally:
        env.close(); summary=log.finish(); print(f"{a.mode}: {summary['successes']}/{summary['trials']}; {log.summary_path}")


if __name__=='__main__': main()
