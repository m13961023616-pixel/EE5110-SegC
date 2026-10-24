"""Record real, captioned development examples, including a planning failure."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
import imageio_ffmpeg
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from clutter_main import source_hash
from robot_manipulation.config import Config
from robot_manipulation.clutter import ClutterEnvironment, compound_obstacles
from robot_manipulation.clutter_planning import ClutterPlanner
from robot_manipulation.active_sensing import ActiveObserver, ActiveConfig
from robot_manipulation.control import Controller
from robot_manipulation.feedback import FeedbackController
from robot_manipulation.recovery import episode
from robot_manipulation.robust_obstacles import symmetric_candidates
from robot_manipulation.local_grasps import local_candidates
from robot_manipulation.video import Recorder
from robot_manipulation.visualization import save_snapshot


def font(size):
    for path in ('C:/Windows/Fonts/arial.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def card(path, title, lines, seconds=6):
    canvas = Image.new('RGB', (800, 600), '#102435')
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((35, 45, 90, 52), fill='#65d6bc')
    y = 82
    for line in textwrap.wrap(title, 33):
        draw.text((35, y), line, font=font(34), fill='white'); y += 45
    y += 30
    for line in lines:
        for wrapped in textwrap.wrap(line, 58):
            draw.text((35, y), wrapped, font=font(23), fill='#cfe1ed'); y += 34
        y += 15
    draw.text((35, 555), 'EE5110 Segment C | actual MuJoCo contact simulation', font=font(16), fill='#65d6bc')
    writer = imageio_ffmpeg.write_frames(str(path), (800, 600), fps=20, codec='libx264', quality=7, macro_block_size=8)
    writer.send(None)
    for _ in range(seconds * 20):
        writer.send(np.asarray(canvas))
    writer.close()


def record(folder, name, scene, strategy, seed, mode='active'):
    env = ClutterEnvironment(Config(spawn_x=(.43, .52), spawn_y=(-.105, -.065), place_xy=(.48, .30)),
                             distractors=3 if scene == 'clutter' else 5, obstacles=compound_obstacles())
    # Only viewing and illumination differ from the ordinary CLI.
    camera = env.model.camera('overview').id
    env.model.cam_pos[camera] = [1.15, 1.15, 1.0]
    x = np.array([-.707, .707, 0.]); x /= np.linalg.norm(x)
    y = np.array([-.35, -.35, .87]); y /= np.linalg.norm(y)
    mujoco.mju_mat2Quat(env.model.cam_quat[camera], np.column_stack((x, y, np.cross(x, y))).ravel())
    env.model.vis.headlight.ambient[:] = .35
    env.model.vis.headlight.diffuse[:] = .75
    env.recorder = Recorder(env, folder / f'{name}.mp4')
    env.recorder.title = f'EE5110 v2.1 | {scene} | {strategy} grasps'
    planner = ClutterPlanner(env, seed=seed + 200001)
    controller = FeedbackController(env, planner) if mode == 'recovery' else Controller(env, planner)
    try:
        def observer(index):
            settings = replace(ActiveConfig(), maximum_frames=128) if index else ActiveConfig()
            return ActiveObserver(settings, seed=seed + 100001 + index * 1000000, instance_mask=True)
        result = episode(env, planner, controller, np.random.default_rng(seed + 1001), 1, 'foam_brick',
                         observer, 2 if mode == 'recovery' else 1,
                         candidate_generator=local_candidates if strategy == 'local' else symmetric_candidates)
        result.update(scene_metrics=env.scene_metrics(), source_sha256=source_hash(),
                      root_seed=seed, scene=scene, strategy=strategy, mode=mode, planner_stats=planner.stats,
                      excluded_from_formal_evaluation=True)
        metrics = result['scene_metrics']
        safe = metrics['unsafe_contact_steps'] == 0 and metrics['distractor_max_displacement_m'] <= .02 and metrics['max_target_penetration_m'] <= .001
        if name != 'baseline_failure' and not (result['success'] and safe):
            raise RuntimeError(f'Demo failed its physical or scene gates: {result}')
        if name == 'baseline_failure' and result['success']:
            raise RuntimeError('Expected the documented development failure')
        (folder / f'{name}.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        save_snapshot(env, folder / f'{name}.png')
        if not result['success']:
            env.recorder.status = 'PLANNING_FAIL: unsafe candidates rejected; no arm motion'
            env.step_for(2.)
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=ROOT / 'outputs/completion_demo_v21')
    parser.add_argument('--output', type=Path, default=ROOT / 'deliverables/demo_v2.1.0.mp4')
    parser.add_argument('--reuse-clips', action='store_true')
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    examples = [('baseline_failure', 'clutter', 'baseline', 20261608, 'active'),
                ('local_recovery', 'clutter', 'local', 20261608, 'active'),
                ('dense_release', 'dense', 'local', 45, 'recovery')]
    for name, scene, strategy, seed, mode in examples:
        if not args.reuse_clips:
            record(args.work, name, scene, strategy, seed, mode)
        print(f'Validated development clip: {name}', flush=True)
    before = json.loads((args.work / 'baseline_failure.json').read_text())
    after = json.loads((args.work / 'local_recovery.json').read_text())
    if before['scene_metrics']['initial_scene'] != after['scene_metrics']['initial_scene']:
        raise RuntimeError('Development comparison has different initial scenes')
    captions = [
        ('intro', 'Autonomous pick and place', ['Franka Panda + public YCB models in MuJoCo.',
         'Question: can a safe alternative grasp clear nearby objects?', 'Real contact, lift, transport, release and independent checks.']),
        ('failure_intro', '1. A useful failure', ['Same development scene: root seed 20261608.',
         'Vertical approaches put the palm into a neighboring can.', 'All candidates are rejected before the arm moves.']),
        ('local_intro', '2. Change the approach', ['Keep original candidates first; add at most 16 alternatives.',
         'Incline 30/45 degrees and offset the contact center 12 mm.', 'The same scene now permits a checked physical release.']),
        ('dense_intro', '3. Five active distractors', ['Development root seed 45; active sensing and bounded feedback.',
         'Distractors retain gravity and collision throughout.', 'The target must settle in the green destination zone.']),
        ('outro', 'What the evidence means', ['Clips are development demonstrations, not success-rate samples.',
         'See the report and complete paired logs for all failures.', 'Known box proxies + ideal masks; real glass remains unverified.']),
    ]
    for name, title, lines in captions:
        card(args.work / f'{name}.mp4', title, lines)
    order = ['intro', 'failure_intro', 'baseline_failure', 'local_intro', 'local_recovery', 'dense_intro', 'dense_release', 'outro']
    concat = args.work / 'concat.txt'
    concat.write_text(''.join(f"file '{(args.work / (name + '.mp4')).resolve().as_posix()}'\n" for name in order), encoding='utf-8')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-y',
                    '-f', 'concat', '-safe', '0', '-i', str(concat), '-c', 'copy', '-movflags', '+faststart', str(args.output)], check=True)
    images = ROOT / 'docs/images'; images.mkdir(parents=True, exist_ok=True)
    evidence = ROOT / 'docs/validation/v2.1.0/demo'; evidence.mkdir(parents=True, exist_ok=True)
    for name, *_ in examples:
        shutil.copy2(args.work / f'{name}.png', images / f'{name}_v2.1.0.png')
        shutil.copy2(args.work / f'{name}.json', evidence / f'{name}.json')
    print(args.output)


if __name__ == '__main__':
    main()
