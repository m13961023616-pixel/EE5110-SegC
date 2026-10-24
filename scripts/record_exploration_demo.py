"""Captioned real-physics examples for all six concrete exploratory directions."""
import argparse
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import imageio_ffmpeg
import mujoco
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.record_completion_demo import card

EXAMPLES=['crowding_single','soft_adaptive','articulated','novel_points','force_adaptive','recovery_retry','sensor_robust']
CAPTIONS={
 'crowding_single':('Crowding and occlusion',['Five dynamic neighbors, four physical obstacles.', 'Two camera directions are strongly occluded.', 'The comparison retains active-view regressions; see report.']),
 'soft_adaptive':('Genuine elastic object',['27 finite-element vertices; 24 reduced deformation DOFs.', 'Real finger contacts deform, lift and release the solid.', 'No rigid visual stand-in, gripper weld or adhesion.']),
 'articulated':('A passive articulated assembly',['The lid hinge stays dynamic under gravity and contact.', 'Grasp and transport the whole assembly.', 'This study does not claim active container opening.']),
 'novel_points':('Unseen procedural instances',['Asymmetric, tapered, notched and held-out wedge shapes.', 'No CAD template or instance mask in grasp estimation.', 'Collision checking still uses simulator geometry.']),
 'force_adaptive':('Force/contact-aware control',['Actual mass, friction and actuator delay vary.', 'Feedback regulates measured finger normal forces.', 'Joint/force limits and physical release checks stay active.']),
 'recovery_retry':('Physical grasp failure and recovery',['A logged actuator fault leaves the first closure too wide.', 'Detect missing contacts; open, withdraw and reobserve.', 'The second physical grasp uses the same scene: one reset.']),
 'sensor_robust':('Correlated depth corruption',['Persistent missing stripes, outliers and calibration bias.', 'Voxel support across independent packets rejects outliers.', 'Synthetic sensing is not real glass refraction.'])}


def record_one(name,work):
    import exploration_main as app
    import robot_manipulation.video as video
    original=video.Recorder
    factory=app.make_environment
    traces=[]
    def environment(case,seed):
        env=factory(case,seed)
        camera=env.model.camera('overview').id
        env.model.cam_pos[camera]=[1.2,1.2,1.05]
        x=np.array([-.707,.707,0.]);x/=np.linalg.norm(x)
        y=np.array([-.35,-.35,.87]);y/=np.linalg.norm(y)
        mujoco.mju_mat2Quat(env.model.cam_quat[camera],np.column_stack((x,y,np.cross(x,y))).ravel())
        env.model.vis.headlight.ambient[:]=.35
        step=env.step;next_time=[0.]
        def instrumented_step():
            step()
            if env.data.time>=next_time[0] and getattr(env,'monitoring',False):
                next_time[0]=env.data.time+.025
                center=env.target_center() if hasattr(env,'target_center') else env.object_pose()[:3,3]
                forces=env.contact_forces() if hasattr(env,'contact_forces') else {}
                angle=env.data.qpos[env.model.jnt_qposadr[env.lid_joint]] if getattr(env,'lid_joint',None) is not None else 0.
                strain=0.
                if getattr(env,'kind',None)=='soft':
                    vertices=env.collision_vertices();edges=env.model.flex_edge
                    lengths=np.linalg.norm(vertices[edges[:,1]]-vertices[edges[:,0]],axis=1)
                    strain=float(np.max(np.abs(lengths/env.reference_lengths-1)))
                traces.append([float(env.data.time),*map(float,center),float(angle),strain,
                               max(forces.values(),default=0.),float(env.max_gripper_force)])
        env.step=instrumented_step
        return env
    app.make_environment=environment
    sys.argv=['exploration_main.py','--headless','--case',name,'--seed','43','--trials','1',
              '--video',str(work/(name+'.mp4')),'--snapshot','--output',str(work/name)]
    try:
        app.main()
    finally:
        app.make_environment=factory
        video.Recorder=original
    with (work/(name+'_trace.csv')).open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream);writer.writerow(['time_s','x_m','y_m','z_m','hinge_rad','edge_strain','normal_force_n','actuator_force_n']);writer.writerows(traces)
    log=next((work/name).glob('trials_*.jsonl'))
    row=json.loads(log.read_text().splitlines()[0])
    if not row['success']:
        raise RuntimeError(f'Development demo {name} failed; its complete log is preserved')
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=ROOT/'outputs/exploration_demo')
    p.add_argument('--output',type=Path,default=ROOT/'deliverables/explorations_v3.0.0.mp4')
    p.add_argument('--reuse-clips',action='store_true')
    a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True)
    for name in EXAMPLES:
        if not a.reuse_clips:record_one(name,a.work)
        print('Validated development example: '+name,flush=True)
    intro=a.work/'intro.mp4'
    card(intro,'Six exploratory directions', ['EE5110 Segment C | v3.0.0',
         'Independent bounded studies, not one universal solver.', '126 new frozen physical episodes; every failure retained.'])
    ending=a.work/'ending.mp4'
    card(ending,'Read the full evidence', ['These clips use development root seed 43.',
         'They are excluded from the 126-episode denominator.',
         'All six topics have limits; negative results are in the report.'])
    order=[intro]
    ff=imageio_ffmpeg.get_ffmpeg_exe()
    for name in EXAMPLES:
        title,lines=CAPTIONS[name]
        title_path=a.work/(name+'_intro.mp4');card(title_path,title,lines+['Physical footage: 2x playback.'])
        accelerated=a.work/(name+'_2x.mp4')
        # Preserve the physical video, label its 2x playback explicitly.
        subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-ss','2','-i',str(a.work/(name+'.mp4')),
            '-vf','setpts=0.5*PTS',
            '-r','20','-c:v','libx264','-crf','20',str(accelerated)],check=True)
        order.extend([title_path,accelerated])
    order.append(ending)
    listing=a.work/'concat.txt';listing.write_text(''.join(f"file '{f.resolve().as_posix()}'\n" for f in order),encoding='utf-8')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(a.output)],check=True)
    evidence=ROOT/'docs/validation/v3.0.0/demo';evidence.mkdir(parents=True,exist_ok=True)
    images=ROOT/'docs/images';images.mkdir(parents=True,exist_ok=True)
    for name in EXAMPLES:
        log=next((a.work/name).glob('trials_*.jsonl'))
        row=json.loads(log.read_text().splitlines()[0]);row['excluded_from_frozen_evaluation']=True
        (evidence/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
        shutil.copy2(a.work/(name+'_trace.csv'),evidence/(name+'_trace.csv'))
        for stage in ('grasp','lift','place'):
            image=a.work/name/f'{name}_1_{stage}.png'
            if image.exists():shutil.copy2(image,images/f'exploration_{name}_{stage}.png')
        if name=='crowding_single':
            shutil.copy2(next((a.work/name).glob('trials_*.png')),images/'exploration_crowding_place.png')
    print(a.output)


if __name__=='__main__':main()
