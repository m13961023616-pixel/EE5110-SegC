"""Export original-speed clips by course requirement, plus baseline visualizations."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile
import imageio_ffmpeg
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CLIPS = [
    ('01_baseline/01_workcell.mp4', '01 工作台与机械臂', 'generated/workcell.mp4', 0),
    ('01_baseline/02_random_YCB_objects.mp4', '02 六种公开 YCB 物体随机摆放', 'generated/random_objects.mp4', 0),
    ('01_baseline/03_grasp_candidates.mp4', '03 算法生成的抓取候选', 'generated/candidates.mp4', 0),
    ('01_baseline/04_pick_and_place.mp4', '04 物理抓取、提升、搬运与放置', 'generated/pick_place.mp4', 2),
    ('01_baseline/05_randomized_trials.mp4', '05 六次平衡随机试验（保留失败）', 'generated/random_trials.mp4', 2),
    ('02_explorations/01_crowding_occlusion.mp4', '拓展 01 密集遮挡', 'exploration_demo/crowding_single.mp4', 2),
    ('02_explorations/02_deformable.mp4', '拓展 02 真正可变形物体', 'exploration_demo/soft_adaptive.mp4', 2),
    ('02_explorations/03_articulated.mp4', '拓展 03 可动铰接物体', 'exploration_demo/articulated.mp4', 2),
    ('02_explorations/04_unseen_shapes.mp4', '拓展 04 未见不规则形状', 'exploration_demo/novel_points.mp4', 2),
    ('02_explorations/05_force_feedback.mp4', '拓展 05 力/接触反馈', 'exploration_demo/force_adaptive.mp4', 2),
    ('02_explorations/06_failure_recovery.mp4', '拓展 06 故障检测与同场景重抓', 'exploration_demo/recovery_retry.mp4', 2),
    ('02_explorations/07_robust_sensing.mp4', '拓展 07 相关深度误差与稳健融合', 'exploration_demo/sensor_robust.mp4', 2),
    ('03_comparisons/01_rejected_grasps.mp4', '对比：原候选被安全拒绝（机械臂不运动）', 'completion_demo_v21/baseline_failure.mp4', 2),
    ('03_comparisons/02_improved_grasps.mp4', '对比：同一场景改进候选后完成抓放', 'completion_demo_v21/local_recovery.mp4', 2),
    ('03_comparisons/03_five_distractors.mp4', '对比：五个动态干扰物中的完整抓放', 'completion_demo_v21/dense_release.mp4', 2),
]


def camera_setup(env, origin=(1.3,1.3,1.0), focus=(.43,0.,.30)):
    cid = env.model.camera('overview').id
    origin = np.array(origin,dtype=float)
    env.model.cam_pos[cid] = origin
    z = origin-np.array(focus); z /= np.linalg.norm(z)
    x = np.cross([0.,0.,1.],z); x /= np.linalg.norm(x)
    y = np.cross(z,x)
    mujoco.mju_mat2Quat(env.model.cam_quat[cid], np.column_stack((x,y,z)).ravel())
    env.model.vis.headlight.ambient[:] = .35


def generate_baseline_visuals(work):
    from robot_manipulation.config import Config
    from robot_manipulation.environment import Environment
    from robot_manipulation.dataset import YCB_OBJECTS
    from robot_manipulation.local_grasps import local_candidates
    from robot_manipulation.perception import observe
    env = Environment(Config(), object_names=list(YCB_OBJECTS))
    camera_setup(env)
    renderer = mujoco.Renderer(env.model, height=600, width=800)
    font = ImageFont.truetype('arial.ttf', 20)
    metadata = {'scope':'development_visualizations_not_evaluation', 'objects':[], 'candidates':[]}
    def record(name, seconds, draw_scene, label):
        writer = imageio_ffmpeg.write_frames(str(work/name), (800, 600), fps=20,
                    codec='libx264', quality=8, macro_block_size=8)
        writer.send(None)
        try:
            for tick in range(round(seconds*20)):
                renderer.update_scene(env.data, camera='overview')
                draw_scene(renderer.scene, tick)
                frame = Image.fromarray(renderer.render())
                drawing = ImageDraw.Draw(frame)
                drawing.rectangle((0, 0, 800, 65), fill='#182532')
                drawing.text((12, 8), label, fill='white', font=font)
                drawing.text((12, 35), 'Development illustration | not a success-rate experiment', fill='#8bd9c5', font=font)
                writer.send(np.asarray(frame))
        finally:
            writer.close()
    try:
        env.reset(np.random.default_rng(43), fixed=True, object_id='foam_brick')
        record('workcell.mp4', 8, lambda s,t:None, 'Workcell: Panda arm, table, YCB target, green placement zone')
        for index, name in enumerate(YCB_OBJECTS):
            env.reset(np.random.default_rng(4343+index), object_id=name)
            metadata['objects'].append({'object':name,'pose':env.object_pose().tolist()})
            record(f'object_{index}.mp4', 3, lambda s,t:None, 'Seeded random placement | public YCB: '+name)
        listing = work/'objects_concat.txt'
        listing.write_text(''.join(f"file '{(work/f'object_{i}.mp4').as_posix()}'\n" for i in range(len(YCB_OBJECTS))), encoding='utf-8')
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y','-f','concat',
                        '-safe','0','-i',str(listing),'-c','copy',str(work/'random_objects.mp4')],check=True)
        env.reset(np.random.default_rng(43), fixed=True, object_id='foam_brick')
        candidates = local_candidates(observe(env), env.config)
        camera_setup(env,origin=(.85,.55,.40),focus=(.48,0.,.10))
        mujoco.mj_forward(env.model,env.data)
        metadata['candidate_generator'] = 'robot_manipulation.local_grasps.local_candidates'
        metadata['candidates'] = [{'index':i,'pose':c.pose.tolist(),'pregrasp':c.pregrasp.tolist(),'width_m':c.width}
                                  for i,c in enumerate(candidates)]
        def axes(scene, tick):
            # Algorithm output only: these poses have not yet passed collision checks.
            selected = candidates[(tick//30) % len(candidates)]
            for candidate in candidates:
                if scene.ngeom >= scene.maxgeom: break
                geom = scene.geoms[scene.ngeom]; scene.ngeom += 1
                mujoco.mjv_initGeom(geom,mujoco.mjtGeom.mjGEOM_SPHERE,np.array([.003]*3),
                    candidate.pregrasp[:3,3],np.eye(3).ravel(),np.array([.5,.7,1.,.7]))
            for axis,color in enumerate(([1.,.2,.2,1.],[.2,1.,.2,1.],[.2,.5,1.,1.])):
                geom=scene.geoms[scene.ngeom];scene.ngeom+=1
                mujoco.mjv_initGeom(geom,mujoco.mjtGeom.mjGEOM_ARROW,np.zeros(3),np.zeros(3),np.eye(3).ravel(),np.array(color))
                mujoco.mjv_connector(geom,mujoco.mjtGeom.mjGEOM_ARROW,.004,selected.pregrasp[:3,3],
                                    selected.pregrasp[:3,3]+.08*selected.pregrasp[:3,axis])
            geom=scene.geoms[scene.ngeom];scene.ngeom+=1
            mujoco.mjv_initGeom(geom,mujoco.mjtGeom.mjGEOM_LINE,np.zeros(3),np.zeros(3),np.eye(3).ravel(),np.array([1.,1.,.3,1.]))
            mujoco.mjv_connector(geom,mujoco.mjtGeom.mjGEOM_LINE,3.,selected.pregrasp[:3,3],selected.pose[:3,3])
        record('candidates.mp4',12,axes,'RGB: pregrasp axes; line: approach | collision checks still needed')
        (work/'visualization_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    finally:
        renderer.close();env.close()


def duration(path):
    result=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-i',str(path)],capture_output=True,text=True)
    match=re.search(r'Duration: (\d+):(\d+):(\d+(?:\.\d+)?)',result.stderr)
    if not match:raise ValueError('Unreadable video duration: '+str(path))
    h,m,s=map(float,match.groups());return h*3600+m*60+s


def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-baseline',action='store_true')
    parser.add_argument('--output',type=Path,default=ROOT/'deliverables/editing_materials')
    args=parser.parse_args()
    work=ROOT/'outputs/editing_materials/generated';work.mkdir(parents=True,exist_ok=True)
    if args.prepare_baseline:
        generate_baseline_visuals(work)
        return
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    ff=imageio_ffmpeg.get_ffmpeg_exe();records=[]
    for target,label,source,trim in CLIPS:
        source_path=(ROOT/'outputs/editing_materials'/source if source.startswith('generated/') else ROOT/'outputs'/source)
        if not source_path.is_file():raise FileNotFoundError(source_path)
        dest=out/target;dest.parent.mkdir(parents=True,exist_ok=True)
        if trim:
            subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-ss',str(trim),'-i',str(source_path),
                            '-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],check=True)
        else:shutil.copy2(source_path,dest)
        # Decode every delivered frame, including videos exported from pre-existing recordings.
        subprocess.run([ff,'-hide_banner','-loglevel','error','-i',str(dest),'-f','null','-'],check=True)
        records.append({'file':target,'label':label,'duration_s':duration(dest),'playback_rate':1.,
                        'source':source_path.relative_to(ROOT).as_posix(),'removed_intro_s':trim,
                        'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
        print(f'{label}: {records[-1]["duration_s"]:.2f}s',flush=True)
    auxiliary=out/'04_analysis_and_logs';auxiliary.mkdir(exist_ok=True)
    for path in (ROOT/'docs/images').glob('exploration_*.png'):shutil.copy2(path,auxiliary/path.name)
    for source in [work/'visualization_metadata.json',*work.glob('summary_*.json'),*work.glob('trials_*.jsonl')]:
        shutil.copy2(source,auxiliary/source.name)
    for source in (ROOT/'docs/validation/v3.0.0/demo').glob('*'):
        if source.is_file():shutil.copy2(source,auxiliary/source.name)
    for name in ('baseline_failure','local_recovery','dense_release'):
        shutil.copy2(ROOT/'outputs/completion_demo_v21'/f'{name}.json',auxiliary/f'{name}.json')
    shutil.copy2(ROOT/'docs/validation/v3.0.0/comparison.json',auxiliary/'formal_126_comparison.json')
    shutil.copy2(ROOT/'docs/DEMO_EDITING_GUIDE.md',out/'00_README.md')
    (out/'CLIP_INDEX.json').write_text(json.dumps({'generated_at':datetime.now().isoformat(),
           'scope':'development_demonstrations_excluded_from_formal_studies','clips':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(out.rglob('*')) if p.is_file() and p.name!='MANIFEST.json'}
    (out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    archive=out.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(out.rglob('*')):
            if path.is_file():z.write(path,path.relative_to(out.parent).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,expected in manifest.items():
            assert hashlib.sha256(z.read(out.name+'/'+name)).hexdigest()==expected
    print(f'Validated {len(records)} original-speed clips, {sum(r["duration_s"] for r in records):.2f}s; ZIP: {archive}')


if __name__=='__main__':main()
