# EE5110 Segment C：自主机器人抓取 baseline

[GitHub 项目](https://github.com/m13961023616-pixel/EE5110-SegC) · [持续集成](https://github.com/m13961023616-pixel/EE5110-SegC/actions/workflows/baseline.yml)

**v1.1.0：基础功能及 90% 性能目标已完成。** Python 3.12、MuJoCo、Franka Panda、六种真实 YCB 网格物体。
随机选择物体和桌面 x/y/yaw，自研抓取候选及过滤，物理接触抓取、完整 pick-and-place 和随机评估。

冻结参数后用新种子独立评估：抓取 **178/180（98.9%）**；完整放置 **175/180（97.2%）**。
95% Wilson 区间分别为 96.0%-99.7%、93.7%-98.8%。六种物体在主要评估中各自成功率也均超过 90%。
另有每物体每任务 20 次的均衡评估，完整统计见 `docs/validation/v1.1.0`。
均衡放置中 pudding_box 为 17/20（85%），这一波动没有隐藏；合并独立 IID 与均衡评估后，每物体每任务均超过 90%，最低为 pudding_box 放置 45/49（91.8%）。
所有失败计入分母，无物理重试或失败后重采样；已知物体、单物体、oracle pose 仿真范围保持明确。
v1.0.0 历史结果为抓取 55%、放置 43.3%，原始证据及报告保留。

## 基础要求对应

| 要求 | 实现与证据 |
|---|---|
| 仿真机器人工作站 | Panda 七轴机械臂、双指夹爪、桌面和放置区 |
| 公开 3D 数据集、随机物体和摆放 | 六种真实 YCB 模型；随机物体/x/y/yaw，固定种子复现 |
| 开发 grasp pose algorithm | 碰撞网格投影、倾斜/侧向候选、开口筛选、评分、全任务预检 |
| grasp 或 pick-and-place | 实际接触抓取、抬升保持、搬运、降低、松爪、退回与判定 |
| 多次随机评估 | 360 次 IID + 240 次均衡实验，JSONL/CSV/JSON、分物体、失败和区间 |
| 报告、介绍视频、源码运行说明 | docs/report/reliability_report_v1.1.0.pdf、版本视频和离线 ZIP、本 README |

## Windows / PyCharm 运行

在项目目录打开 PyCharm，选择 `.venv/Scripts/python.exe`。已有环境直接运行 `main.py`，默认 GUI 随机 YCB 抓取一次。
新环境在项目根目录 PowerShell 执行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/setup_assets.py
.\.venv\Scripts\python.exe scripts/setup_ycb.py
.\.venv\Scripts\python.exe main.py --object foam_brick --fixed --task place --keep-open
```

下载脚本固定 commit 并校验 SHA-256，完整缓存不重复下载。仅源码安装首次需要网络。
模型目录 assets/panda 和 assets/ycb 不上传 Git；离线交付 ZIP 包含模型及上游许可证。
PyCharm Run Configuration：Script=main.py，Working directory=项目根目录，Parameters 按下面示例设置。

```powershell
# 正式随机评估；所有失败保留
.\.venv\Scripts\python.exe main.py --headless --trials 180 --seed 20261011
.\.venv\Scripts\python.exe main.py --headless --trials 180 --seed 20261012 --task place
# 复现全部四组性能验证；任一组低于 90% 时返回失败
.\.venv\Scripts\python.exe scripts/benchmark_reliability.py
# cube 仅用于回归，不替代公开数据集
.\.venv\Scripts\python.exe main.py --headless --dataset cube --fixed --task place --require-all-success
# 十二项测试，包含六物体完整放置、力上限和资产下载验证
.\.venv\Scripts\python.exe tests/test_baseline.py
.\.venv\Scripts\python.exe tests/test_dataset.py
.\.venv\Scripts\python.exe tests/test_asset_setup.py
# 可选真实仿真 MP4 录制，需要 OpenGL
.\.venv\Scripts\python.exe -m pip install -r requirements-video.txt
.\.venv\Scripts\python.exe main.py --headless --object foam_brick --fixed --task place --video outputs/demo.mp4
```

`--fast` 加速 GUI，`--snapshot` 保存最终 PNG，`--output 路径` 指定日志目录。
`--balanced` 将六物体按随机顺序各运行一次后开启下一组，便于均衡覆盖。
YCB 默认随机摆放，`--fixed` 固定调试；cube 需 `--randomize` 才随机。
普通评估允许失败，正常结束返回 0，真实结果以 summary 为准；`--require-all-success` 任一次失败返回 1。
中断返回 130，并保留已完成 trial。

## 算法和判定

reset → oracle pose/碰撞几何 → shape-aware candidates → 全任务可行性预检 → close → lift → hold。
place 模式继续 transfer → lower → open → retreat → verify place。
pose 统一 T_A_B（B 到 A），IK 为带关节限制的 damped least squares。
关节插值与 Cartesian waypoints 做离散碰撞检查；smoothstep 关节目标和渐进夹爪目标驱动官方 actuator。
执行不瞬移、不 weld；scratch planning 的相对抓取变换只用于预测搬运碰撞。

接触使用 elliptic 摩擦锥、impratio=10、YCB condim=6；不提高原有摩擦数值来强制成功。
夹爪刚度 1000 N/m，接触后固定柔顺预载开口，actuator 力上限 40 N；机械臂增加偏置力补偿。
抓取和降低使用实际编译后的 CoACD 碰撞几何，避免视觉模型边界差异导致高度偏低。
grasp 候选预检 lift 和 place，执行时再检查 transfer/lower；放置候选偏移最大每轴 2 cm，仍在原目标判定范围内。
各组保存源代码 SHA-256、版本、参数和峰值夹爪力，便于检查复现条件。

抓取成功：1 秒保持中物体中心始终比初始高至少 8 cm，至少 95% 样本有双侧夹爪接触。
放置还需：目标中心距离小于 5.5 cm、桌面接触、夹爪释放、线速度小于 0.02 m/s。
全部失败进入分母，不重采样隐藏失败。

## 适用范围与限制

- 感知使用仿真真实位姿，尚无图像分割、RGB-D 位姿估计或 learned grasping。
- 单物体；包装盒直立初始化后自然静置；随机 x/y/yaw，不覆盖任意 roll/pitch 或杂乱堆叠。
- 保持 YCB 原始尺寸、纹理和声明质量；CoACD 凸分解碰撞、包围盒近似惯量、显式未标定摩擦参数。
- 结构化规划拒绝阻挡路径，不搜索绕障；碰撞是离散采样，无连续保证。
- 仍有少量真实碰撞失败，全部记录。pudding_box 改用稳定端面初始化，保持原生尺寸与质量。
- 前后差异包括接触求解、控制和初始化修正，不将增益全部归因于算法；材料与真实机械臂尚未标定。
- 新视频是固定 lemon 的成功展示，不能代替完整随机统计。

## 代码导览与交付

| 文件 | 职责 |
|---|---|
| main.py | PyCharm/CLI 入口和实验循环 |
| robot_manipulation/dataset.py、environment.py | 数据集、场景、reset、物理状态与接触 |
| perception.py、grasp.py | 真实位姿观测、网格抓取候选 |
| planning.py、control.py | IK、路径校验、actuator 执行 |
| pipeline.py、evaluation.py | 完整任务、结果判定、统计 |
| config.py | 集中配置；长度 m、角度 rad |
| docs/validation/v1.0.0 | 120 次正式随机实验的全部证据 |
| docs/report/baseline_report.pdf | 英文报告：需求、算法、结果与局限 |
| docs/validation/v1.1.0 | 600 场景性能验证、冻结方案、源指纹和全部失败 |
| docs/report/reliability_report_v1.1.0.pdf | 新版性能报告、分物体结果、控制/接触配置和范围 |
| scripts/benchmark_reliability.py | 复现四组独立性能评估 |
| scripts/build_reliability_report.py | 从四组正式证据重建新版 PDF，需 reportlab |
| scripts/build_report.py | 从正式实验重建 PDF，需 reportlab |
| scripts/package_submission.py | 生成含源码、模型、报告、视频的离线 ZIP |
| PROGRESS.md、CHANGELOG.md | 进度、验证与版本记录 |

本地交付：`deliverables/EE5110SegC_baseline_v1.1.0.zip`、`deliverables/reliability_demo_v1.1.0.mp4`。
ZIP 排除 .git、.venv、.idea、凭据、课程原始文件和临时输出。
报告没有虚构团队成员；实际成员身份和最终提交信息需自行补充。
GitHub 按完整阶段维护分支、PR、验证和标签，避免小功能频繁发布。

接触求解配置依据：[MuJoCo 接触建模说明](https://mujoco.readthedocs.io/en/stable/modeling.html)。

## 归属与许可

[YCB Object and Model Set](https://ycb-benchmarks.s3.amazonaws.com/index.html)：数据 CC BY 4.0。
[elpis-lab/YCB_Dataset](https://github.com/elpis-lab/YCB_Dataset)：转换 MIT，固定版本见 assets/ycb.lock.json。
[MuJoCo Menagerie Panda](https://github.com/google-deepmind/mujoco_menagerie/tree/main/franka_emika_panda)：
版本及校验见 assets/panda.lock.json，上游许可证随模型下载并包含于离线 ZIP。
