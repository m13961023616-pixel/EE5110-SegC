# 分段视频素材与 MuJoCo 演示界面

## 一、直接拿去剪辑的素材

项目根目录下的 `deliverables/editing_materials/` 保存逐项视频；`deliverables/editing_materials.zip` 可整体复制到其他电脑。双击 MP4 即可播放，也可以导入剪映、Premiere 或 DaVinci Resolve。

共 15 段独立 MP4，800×600、20 fps、无音轨。执行片段从原始录像导出，没有进行倍速处理，去掉了单段录像开头的 2 秒通用说明卡；保留顶部英文阶段栏，便于识别接近、提升、搬运、下降和任务结果。最终 v3 合成视频中的 2 倍速没有用于这里。所有素材都是开发演示，不进入原有 126/180 次正式实验分母。

| 课程部分 | 素材路径（相对于 editing_materials） | 内容与剪辑提示 |
|---|---|---|
| 构建仿真工作台 | `01_baseline/01_workcell.mp4` | 8 秒已建立场景的静态展示，含 Panda、桌面、YCB 目标和绿色放置区；适合开场。不是工作台搭建过程录像。 |
| 公开数据集随机选物、摆放 | `01_baseline/02_random_YCB_objects.mp4` | 六种 YCB 物体按种子随机位置/角度分别摆放，每种 3 秒。物体按目录逐个展示；随机选择/平衡抽样的真实执行见第 05 段。 |
| 算法生成抓取姿态 | `01_baseline/03_grasp_candidates.mp4` | 从真实场景观测生成局部候选，轮流显示预抓取姿态的红绿蓝坐标轴，连线指向目标抓取姿态，12 秒。显示的是生成结果，尚未保证全部通过碰撞检查；不是抓取执行视频。 |
| 控制机械臂完成抓取/放置 | `01_baseline/04_pick_and_place.mp4` | 单个 foam_brick 的完整物理抓放，适合按英文阶段栏拆成接近、闭合、提升、搬运、张开释放和撤离。 |
| 多次随机实验评估 | `01_baseline/05_randomized_trials.mp4` | 一次开发运行中的六个平衡随机物体场景，依次独立初始化。结果/失败原样保留；不要把这个演示当成正式可靠性统计。 |
| 密集/严重遮挡 | `02_explorations/01_crowding_occlusion.mp4` | 五个动态邻物、实体屏障与遮挡屏中的抓放。 |
| 可变形物体 | `02_explorations/02_deformable.mp4` | 真正弹性 flex 物体的接触、提升与释放，可配套应变/力图讲解。 |
| 铰接物体 | `02_explorations/03_articulated.mp4` | 被动转轴保持可动的整件搬运，不是主动开盖。 |
| 未见/不规则物体 | `02_explorations/04_unseen_shapes.mp4` | 新形状从无 CAD 输入的点云抓取估计开始完成搬运；规划/控制仍使用仿真几何。 |
| 力/接触反馈 | `02_explorations/05_force_feedback.mp4` | 在实际质量、摩擦和指令延迟变化下用接触反馈抓放；具体力变化配合 CSV/曲线说明。 |
| 失败检测与恢复 | `02_explorations/06_failure_recovery.mp4` | 第一次故障闭合抓不到目标，随后张开、撤离、回位、重观测、第二次成功；全程同一场景。 |
| 更现实的感知/物理条件 | `02_explorations/07_robust_sensing.mp4` | 受损点云的稳健估计驱动抓放；相机误差本身需配合点云对比图展示，不能仅凭机器人画面看出。 |
| 失败对比补充 | `03_comparisons/01_rejected_grasps.mp4` | 不安全候选被规划器拒绝，因此机械臂不运动，是预期的失败演示。 |
| 改进对比补充 | `03_comparisons/02_improved_grasps.mp4` | 与上一段完全相同的开发场景，增加候选后完成抓放。 |
| 五干扰物补充 | `03_comparisons/03_five_distractors.mp4` | 另一段五动态干扰物中的完整抓放。 |

`CLIP_INDEX.json` 列出每段标签、准确时长、源录像路径、去除片头长度和 SHA-256；`MANIFEST.json` 校验整套素材。`04_analysis_and_logs/` 包含实际力/应变/铰接角 CSV、对应图片、候选姿态、随机试验结果和演示日志。用于解释机制的曲线来自开发片段，正式成功率仍引用报告/`formal_126_comparison.json`。

可按“工作台 → 数据集 → 候选 → 完整抓放 → 随机评估 → 各拓展 → 成功/失败对比”的顺序剪辑。课程要求带介绍的最终演示；分段素材本身没有补写解说或配音，可以自行加中文介绍。没有为开放性的“其他有意义拓展”虚构一个无穷尽的任务清单。

## 二、最简单的界面打开方法

**双击项目根目录 `OPEN_DEMO.cmd`。** 出现控制台菜单，输入序号并按 Enter，就会打开 MuJoCo 交互窗口，自动执行该项演示。开始前可能需要等待模型加载/规划；运行结束后窗口保持，方便转动视角。关闭 MuJoCo 窗口结束本次运行，重新双击可选择另一项。

菜单包含基础抓放、密集遮挡、软体、铰接、未见形状、力反馈、故障恢复和稳健感知。新启动器在拓展模型构建完成后才连接窗口，直接显示实际运行的模型；不会修改已冻结的实验引擎。

- 鼠标左键拖动：旋转视角；右键拖动：平移；滚轮：缩放。
- 空格：本启动器暂停/继续物理执行；开始前想检查场景，可使用下面的 `--start-paused`。
- 执行结束后只刷新画面，不继续推进物理时间；鼠标仍可调整视角。
- 日志保存在 `outputs/gui_demo/`。这是交互开发演示，不是正式批量实验。

在 PowerShell 中直接打开指定演示：

```powershell
Set-Location 'C:\Users\86138\Desktop\segment c\EE5110-SegC'
.\.venv\Scripts\python.exe demo_viewer.py --case baseline
.\.venv\Scripts\python.exe demo_viewer.py --case soft_adaptive
.\.venv\Scripts\python.exe demo_viewer.py --case articulated
.\.venv\Scripts\python.exe demo_viewer.py --case recovery_retry
.\.venv\Scripts\python.exe demo_viewer.py --case sensor_robust --start-paused
```

`--case` 还接受全部 14 个实验条件名称，可打开固定控制/反馈控制、单帧/融合等对照。默认开发种子 43，尽量按实时速度播放；计算和规划仍可能让画面停留或运行较慢。`--fast` 取消限速，`--auto-close` 在任务结束后自动关窗。

如果只想看原有基线界面，仍可用：

```powershell
.\.venv\Scripts\python.exe main.py --object foam_brick --task place --fixed --keep-open
.\.venv\Scripts\python.exe clutter_main.py --scene dense --object foam_brick --seed 45 --trials 1
```

这些原有入口不使用 `--headless` 时会显示窗口；`exploration_main.py` 默认是批量无界面入口，观看拓展请用 `demo_viewer.py`。直接执行旧 `clutter_main.py` 会在任务结束后关闭，想保持画面建议使用新菜单。

## 三、重新导出与新电脑

本机 `.venv` 已建立，直接双击启动即可。不要单独把 `.venv` 复制到别的电脑；新电脑按 [拓展交付指南](EXPLORATION_HANDOVER.md) 安装 Python 3.12、依赖和模型。交互窗口需要本机可用的图形桌面和 OpenGL 驱动，不需要浏览器或服务器。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-video.txt
.\.venv\Scripts\python.exe scripts/prepare_editing_materials.py --prepare-baseline
.\.venv\Scripts\python.exe main.py --headless --object foam_brick --task place --fixed --seed 43 --trials 1 --video outputs/editing_materials/generated/pick_place.mp4 --output outputs/editing_materials/generated
.\.venv\Scripts\python.exe main.py --headless --balanced --task place --seed 43 --trials 6 --video outputs/editing_materials/generated/random_trials.mp4 --output outputs/editing_materials/generated
.\.venv\Scripts\python.exe scripts/prepare_editing_materials.py
```

导出脚本还依赖前一阶段已经生成的 `outputs/exploration_demo/*.mp4` 和 `outputs/completion_demo_v21/*.mp4`；若这些源文件不存在，先运行 `scripts/record_exploration_demo.py`、`scripts/record_completion_demo.py`。不要用 `*_2x.mp4` 替代原速源文件。导出会逐帧完整解码检查全部 15 段视频，并校验压缩包文件哈希。
