"""Interactive live demonstrations without modifying either frozen experiment engine."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import threading
import time
import sys
import mujoco
from mujoco import viewer
import numpy as np
from exploration.protocol import CASES
from exploration.provenance import source_hash
from exploration.runner import make_environment, run_case_episode
from robot_manipulation.config import Config, ROOT
from robot_manipulation.environment import Environment
from robot_manipulation.planning import Planner
from robot_manipulation.control import Controller
from robot_manipulation.pipeline import trial

MENU = [
    ('baseline', '基础：YCB 物体完整抓取与放置'),
    ('crowding_single', '拓展：密集物体与严重遮挡'),
    ('soft_adaptive', '拓展：真正的弹性软体'),
    ('articulated', '拓展：被动铰接物体'),
    ('novel_points', '拓展：未见不规则物体与点云抓取估计'),
    ('force_adaptive', '拓展：接触力反馈与随机物理'),
    ('recovery_retry', '拓展：实际抓取失败后的同场景恢复'),
    ('sensor_robust', '拓展：相关深度误差与稳健融合'),
]


class Display:
    """Keep rendering at most 60 Hz even when soft physics steps at 1000 Hz."""
    def __init__(self, handle):
        self.handle = handle
        self.next_refresh = 0.

    def __getattr__(self, name):
        return getattr(self.handle, name)

    def sync(self):
        now = time.perf_counter()
        if now >= self.next_refresh:
            self.handle.sync()
            self.next_refresh = now+1/60


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['baseline', *CASES])
    parser.add_argument('--seed', type=int, default=43)
    parser.add_argument('--fast', action='store_true', help='Disable real-time pacing')
    parser.add_argument('--auto-close', action='store_true', help='Close the window when execution ends')
    parser.add_argument('--start-paused', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT/'outputs/gui_demo')
    args = parser.parse_args()
    if args.case is None:
        print('MuJoCo 演示菜单（输入序号，再按 Enter；0 退出）')
        for i, (_, label) in enumerate(MENU, 1):
            print(f'{i}. {label}')
        while True:
            choice = input('选择：').strip()
            if choice == '0':
                return 0
            if choice.isdigit() and 1 <= int(choice) <= len(MENU):
                args.case = MENU[int(choice)-1][0]
                break
            print('请输入菜单中的数字。')
    env = (Environment(Config(), object_names=['foam_brick']) if args.case == 'baseline'
           else make_environment(CASES[args.case], args.seed+300001))
    # ResearchEnvironment recompiles its model. Launch only after that is complete.
    paused = threading.Event()
    if args.start_paused:
        paused.set()
    def key_callback(key):
        if key == 32:
            if paused.is_set(): paused.clear()
            else: paused.set()
    interrupted = False
    row = None
    try:
        env.viewer = Display(viewer.launch_passive(env.model, env.data, key_callback=key_callback))
        env.viewer.cam.lookat[:] = [.46, .08, .18]
        env.viewer.cam.distance = 1.35
        env.viewer.cam.azimuth = 45
        env.viewer.cam.elevation = -25
        env.model.vis.headlight.ambient[:] = .35
        env.realtime = not args.fast
        physical_step = env.step
        def pausable_step():
            while paused.is_set():
                if not env.viewer.is_running():
                    raise KeyboardInterrupt
                env.viewer.sync()
                time.sleep(.02)
            physical_step()
        env.step = pausable_step
        print(f'Live MuJoCo viewer opened: {args.case}', flush=True)
        print('空格：暂停/继续；鼠标左键拖动：旋转；右键拖动：平移；滚轮：缩放。', flush=True)
        print('规划可能短暂停留；结束后画面保持静止，可转动视角。关闭仿真窗口退出。', flush=True)
        if args.case == 'baseline':
            planner = Planner(env)
            row = trial(env, planner, Controller(env, planner), np.random.default_rng(args.seed),
                        1, fixed=True, object_id='foam_brick', task='place')
        else:
            row = run_case_episode(env, CASES[args.case], args.seed, 1)
        row.update(case=args.case, source_sha256=source_hash(), development_demonstration=True,
                   excluded_from_frozen_evaluation=True)
        args.output.mkdir(parents=True, exist_ok=True)
        log = args.output/f'{args.case}_{datetime.now():%Y%m%d_%H%M%S_%f}.json'
        log.write_text(json.dumps(row, indent=2)+'\n', encoding='utf-8')
        print(f"Result: {row['failure_stage']}; log: {log}", flush=True)
        if not args.auto_close:
            # Inspection does not add physics steps to the completed trial.
            while env.viewer.is_running():
                env.viewer.sync()
                time.sleep(1/60)
    except KeyboardInterrupt:
        interrupted = True
        print('演示已停止。', flush=True)
    finally:
        env.close()
    return 130 if interrupted else int(row is not None and not row['success'])


if __name__ == '__main__':
    raise SystemExit(main())
