"""Reproduce the development dense-clutter demo from the placement side.

Camera and goal marker are visualization only; benchmark physics is unchanged.
"""
from pathlib import Path
import sys
import json
import mujoco
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from robot_manipulation.clutter import ClutterEnvironment, compound_obstacles
from robot_manipulation.clutter_planning import ClutterPlanner
from robot_manipulation.config import Config
from robot_manipulation.feedback import FeedbackController
from robot_manipulation.active_sensing import ActiveObserver
from robot_manipulation.recovery import episode
from robot_manipulation.visualization import save_snapshot
from robot_manipulation.video import Recorder


def main():
    env=ClutterEnvironment(Config(place_xy=(.48,.30)),distractors=5,obstacles=compound_obstacles())
    camera=env.model.camera('overview').id
    env.model.cam_pos[camera]=[1.3,1.3,1.1]
    x=np.array([-.707,.707,0.]);x/=np.linalg.norm(x)
    y=np.array([-.35,-.35,.87]);y/=np.linalg.norm(y)
    mujoco.mju_mat2Quat(env.model.cam_quat[camera],np.column_stack((x,y,np.cross(x,y))).ravel())
    env.model.site_pos[env.model.site('place_target').id,:2]=env.config.place_xy
    output=ROOT/'deliverables/clutter_v2.0.0.mp4'
    env.recorder=Recorder(env,output);env.recorder.title='EE5110 v2.0 | Transparent proxy + 5 physical distractors'
    planner=ClutterPlanner(env,seed=200046)
    try:
        r=episode(env,planner,FeedbackController(env,planner),np.random.default_rng(1046),1,'foam_brick',
                  lambda i:ActiveObserver(seed=100046+i*1000000,instance_mask=True))
        assert r['success'] and env.unsafe_contact_steps==0 and env.maximum_distractor_displacement<=.02,r
        save_snapshot(env,ROOT/'docs/images/clutter_place_v2.0.0.png')
        folder=ROOT/'outputs/v2_demo_placement_view';folder.mkdir(exist_ok=True)
        r['scene_metrics']=env.scene_metrics();(folder/'recording_result.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
        print(output)
    finally:env.close()


if __name__=='__main__':main()
