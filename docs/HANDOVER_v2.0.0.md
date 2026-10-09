# EE5110 Segment C 小组项目交接文档

交接日期：2026-10-09。交接基线：`v2.0.0`。本文面向接手优化、验证和最终报告整合的组员。

本文区分已验证事实、代码实现假设和后续建议。课程评分标准以教师发布的原始 CA 文件为准；本文记录实际工程状态，不构成教师验收结论，也不预填组员身份或贡献。

## 1. 交接结论与阅读顺序

项目已经具备可运行的 Panda 机械臂物理 pick-and-place 系统、公开 YCB 模型随机实验、实体障碍规划、合成透明目标感知，以及带三个/五个活动干扰物和三组件固定障碍的联合场景。

v2.0.0 的三个目标是透明外观的 `foam_brick`、`gelatin_box`、`pudding_box`。目标由双指实际接触夹持，抬升、搬运、松爪和稳定放置；没有使用运行过程中的物体瞬移、粘附或 weld 代替抓取。干扰物在执行中保持碰撞与重力。

**必须保留的结论边界：** 透明目标是已知盒形的合成代理，使用理想实例掩码和仿真碰撞地图，尚未解决真实玻璃折射、未知形状识别或堆叠杂乱抓取。三干扰物完整任务为 52/60，五干扰物为 25/30，不能表述为 clutter 已达到 90%。

建议新组员依次完成：

1. 阅读本文第 2–4 节，安装环境并跑通一个真实物理成功案例。
2. 阅读第 5–8 节，对照日志理解模块、成功判据和证据口径。
3. 阅读第 9–11 节，选择一个优化任务，先复现失败，再制定冻结评估方案。
4. 阅读第 12–14 节，按 Git/证据规则提交完整阶段并完成组内交接核验。

## 2. 仓库、版本与交付物

| 项目 | 交接状态 |
|---|---|
| 公共仓库 | https://github.com/m13961023616-pixel/EE5110-SegC |
| 稳定标签 | `v2.0.0`；后续比较应以标签源码为基线 |
| 标签对应提交 | `28a16c74b7beee1dcd8f2376801cf53da623dfe0` |
| 功能合并 PR | https://github.com/m13961023616-pixel/EE5110-SegC/pull/6 |
| 发布页 | https://github.com/m13961023616-pixel/EE5110-SegC/releases/tag/v2.0.0 |
| 正式实验 | `docs/validation/v2.0.0/`，六组，共 270 个物理 episode |
| 正式报告 | `docs/report/clutter_v2.0.0.pdf`，四页英文报告 |
| 实际演示 | 发布附件 `clutter_v2.0.0.mp4` |
| 离线交付 | 发布附件 `EE5110SegC_baseline_v2.0.0.zip`，含源码、模型、许可证、报告、视频 |
| 当前 Windows 工作区 | `F:\NUS\Semester I\EE5110\Segment C\CA` |
| 环境 | 项目根目录 `.venv`，Python 3.12 |

v2.0.0 发布时，PR、main 和标签的 GitHub Actions 均成功，34 项本地测试通过；独立解压 ZIP 的证据审计和五干扰物物理成功案例也通过。main/标签的成功 CI 记录为 `37907855754` / `37907862703`。这是该版本的历史验证事实，不代表任何后续修改自动通过。

本交接文档属于发布后的文档补充；旧标签、旧报告和旧发布 ZIP 不会被重写。组员应从更新后的仓库取得本文。

### 2.1 历史版本用途

| 版本 | 内容与代表性结果 | 不能混用的范围 |
|---|---|---|
| v1.1.0 | 六物体单目标 baseline；IID 放置 175/180，抓取 178/180；四组共 600 次 | 已知姿态、单物体，不能当作透明 clutter 成功率 |
| v1.2.0 | 实体挡板与三种规划对照；共 360 次 | 单物体障碍挑战 |
| v1.3.0 | 障碍可靠性；22 cm 112/120，28 cm 108/120；新旧配对共 480 次 | 对应精确历史源码，不是当前联合场景 |
| v1.4.0 | 三种透明外观盒形代理；双视角融合 59/60；四组共 240 次 | 单目标合成深度实验，不含正式 clutter |
| v2.0.0 | 主动感知、接触反馈/有限恢复、活动干扰物与复杂障碍；共 270 次 | 已知盒形、理想实例掩码、合成传感器、仿真地图 |

## 3. 组员首次运行

以下 PowerShell 命令均在项目根目录执行。其他电脑可使用任意本地路径，不依赖 F 盘。

### 3.1 从 Git 克隆

```powershell
git clone https://github.com/m13961023616-pixel/EE5110-SegC.git
Set-Location EE5110-SegC
git fetch --tags
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/setup_assets.py
.\.venv\Scripts\python.exe scripts/setup_ycb.py
```

核心依赖固定为 `mujoco==3.15.0`、`numpy==2.5.3`；正式本地记录的 Python 为 3.12.10。不要直接升级依赖后把结果归属于 v2.0.0。模型下载脚本按锁文件固定 commit 并核验 SHA-256，完整缓存无需重复下载。

Panda 锁定 commit：`0059d4335f8156206f63a35662313385f7ad6d74`。YCB 转换仓库锁定 commit：`9e8c6488a2ff673d9aa48a91492fb89423c1b106`。以 `assets/panda.lock.json`、`assets/ycb.lock.json` 为准。

### 3.2 从离线 ZIP 接手

解压发布 ZIP 到新目录，建立 `.venv` 并安装核心依赖；模型已经包含在 ZIP 中，不必重新下载。这里“离线包”指模型和项目文件齐全，**不包含 Python 环境或 pip wheel**；完全断网的电脑仍需自行准备 Python 和依赖安装包。

ZIP 不包含 `.git`，不能用它审计需要历史 Git 标签的旧实验。当前 v2 证据可直接审计；长期协作和历史比较建议使用 Git 克隆。

### 3.3 首个验证案例

```powershell
# 验证现有270条冻结证据，不重新跑270次物理实验
.\.venv\Scripts\python.exe scripts/check_v2_evidence.py --source-ref v2.0.0

# 已通过独立离线包验证的五干扰物实际夹放案例
.\.venv\Scripts\python.exe clutter_main.py --headless --scene dense --object foam_brick --seed 45 --trials 1 --require-all-success --output outputs/onboarding_dense

# GUI：三种目标均衡顺序，默认主动感知+最多两次尝试
.\.venv\Scripts\python.exe clutter_main.py --scene clutter --trials 3
```

离线 ZIP 没有 Git 时，第一条命令去掉 `--source-ref v2.0.0`，直接校验当前源码。后续修改 engine 后，也不能去掉历史标签参数然后要求旧证据匹配新源码。

PyCharm：Interpreter 选 `.venv\Scripts\python.exe`；Script 选 `clutter_main.py`；Working directory 设项目根目录；Parameters 例如 `--scene dense --trials 3`。不要误用系统 Python 或历史入口。

GUI 在仿真完成后关闭是当前入口行为，`clutter_main.py` 没有 `--keep-open` 参数。普通运行进程返回 0 只代表程序正常结束；是否任务成功必须看 summary。指定 `--require-all-success` 后，任一任务失败会返回 1。

### 3.4 入口和参数

| 入口/参数 | 含义 |
|---|---|
| `main.py` | 原始单物体 baseline，默认任务与 v2 不同；适合基础回归 |
| `challenge_main.py` | 历史单物体障碍入口 |
| `sensing_main.py` | 历史透明代理感知对照 |
| `clutter_main.py` | v2 联合场景的首选入口 |
| `--scene isolated` | 无干扰物、无固定障碍 |
| `--scene obstacles` | 无干扰物，三个固定障碍组件 |
| `--scene clutter` / `dense` | 三个 / 五个活动干扰物，均有三个固定障碍组件 |
| `--mode fixed` | 固定64帧、三视角循环、普通控制、一次尝试 |
| `--mode active` | 有界主动观测、普通控制、一次尝试 |
| `--mode recovery` | 主动观测+反馈控制，最多两次尝试；默认模式 |
| `--object` | 仅允许上述三种透明目标；不指定时三物体按随机排列分块均衡 |
| `--seed` / `--trials` | 根随机种子 / episode 数；默认43 / 3 |
| `--height` | 挡板高度，默认0.22 m，允许0.12–0.28 m；两根立柱保持0.18 m |
| `--dropout` / `--permanent-dropout` | 独立随机缺失 / 每视角固定缺失；默认0.98 / 0.10 |
| `--output` | 新日志目录，建议每个实验使用不同目录 |
| `--video` / `--snapshot` | 可选视频 / 最终图片；需相应渲染环境与依赖 |

`fixed` 是固定观测策略，**不是固定物体摆放**。三个方法均随机生成物理场景。

## 4. 当前场景和感知假设

### 4.1 真实物理场景

目标初始 x 在 [0.43, 0.52] m，y 在 [-0.105, -0.065] m，yaw 随机；包装目标采用已知稳定 roll。放置判定中心为 `(0.48, 0.30)` m。场景初始化后自然静置0.8秒，再记录初始姿态并开启执行监测。

邻物使用相对于目标的五个预设偏移：`(-.105,-.005)`、`(.11,-.015)`、`(.01,.11)`、`(-.115,.105)`、`(.125,.12)` m，各坐标再加±4 mm jitter及随机yaw。这是靠近但有结构的桌面 clutter，**不是随机堆叠或相互紧贴的无序物体堆**。

干扰物优先序为 tomato_soup_can、lemon、strawberry、gelatin_box、pudding_box、foam_brick，剔除目标后取前3或前5个。因此三目标类别改变时，干扰物组成也可能改变；不能把分目标差异全部归因于目标材质。

默认障碍：挡板中心 `(0.485,0.145,0.11)` m、半尺寸 `(0.12,0.008,0.11)` m；立柱中心 `(0.34,0.215,0.09)`、`(0.64,0.205,0.09)` m，半尺寸分别为 `(.018,.052,.09)`、`(.018,.055,.09)` m。

只对本次目标视觉几何去纹理并设 alpha=0.25。质量、尺寸、摩擦和接触碰撞属性不因透明外观而改变。初始化自由体姿态以及 scratch 规划中的假想持物关系不属于实时物理执行；不得把类似状态写入引入实际搬运来提高成功率。

### 4.2 感知与真值依赖的分界

| 环节 | 实际依赖 |
|---|---|
| 合成观测生成 | MuJoCo几何射线、理想相机标定、实例归属 |
| 目标分割 | 理想 simulator instance mask；没有训练识别模型 |
| 位姿估计 | 带缺失/噪声的测量点、已知目标类别/网格、upright先验 |
| 抓取候选 | 估计的 `T_world_object` 与已知几何 |
| 碰撞规划、持物预测、降低几何 | 仿真状态与碰撞模型 |
| 接触反馈和最终评估 | 仿真接触身份、力、真实物体状态 |

估计器不会在失败时回退真实目标位姿，但整个系统仍不是纯图像驱动。宣称“无真值”必须限定到位姿估计器，不能扩展到整个规划和验证链路。

合成传感器为96×96正交射线，三个预设上方/斜向视角，98%独立缺失、每视角10%固定缺失、0.5 mm z噪声。alpha只影响外观，不模拟真实折射、镜面多路径或玻璃破碎。

主动观测每批8帧，最少16帧、首次最多64帧；检查至少48个不同前景点、水平轮廓误差≤6 mm、相邻估计平移变化≤3 mm及yaw变化≤0.08 rad。这些是几何启发式，不是校准的成功概率。固定策略即使未通过主动置信度判据，只要有有效拟合，64帧后仍可返回拟合结果。

恢复入口第二次观测最多128帧，传感器种子增加1,000,000。名义串行采集时间为帧数/30秒；当前采集不会推进物理仿真时间，不代表真实相机闭环速度。

## 5. 模块和数据流

| 文件 | 接手时重点关注 |
|---|---|
| `clutter_main.py` | CLI、目标序列、三类种子、模式组合、外层场景保护门槛、engine指纹 |
| `robot_manipulation/config.py` | 统一物理/控制/判定配置；v2入口覆盖spawn和place坐标 |
| `environment.py` / `dataset.py` | 模型编译、状态、几何、资产接口、接触查询 |
| `clutter.py` | 活动干扰物、初始化、持续邻物位移与不安全接触监测 |
| `active_sensing.py` / `depth_sensing.py` | 合成观测、点拟合、主动置信度；目标识别不是这里的现成能力 |
| `grasp.py` / `robust_obstacles.py` | 网格候选、开口过滤、候选评分、180°等价双指朝向、九个IK初值 |
| `planning.py` / `search.py` | 核心规划接口与IK、离散边校验、RRT-Connect搜索 |
| `obstacle_planning.py` / `clutter_planning.py` | 越障通道、RRT fallback、放置中心/朝向候选与下放预检 |
| `control.py` / `feedback.py` | actuator执行、双指接触力监测、有限预载调整、持续失联停止 |
| `pipeline.py` | 单次尝试：观测→候选→全任务预检→执行→物理判定 |
| `recovery.py` | 一次物理scene内有限尝试、安全退回、首次/最终结果和动作汇总 |
| `evaluation.py` | 提升/释放/稳定判定、JSONL/CSV/summary、Wilson区间 |
| `scripts/benchmark_v2.py` | 六组冻结比较的运行器 |
| `scripts/check_v2_evidence.py` | 正式记录、历史源码、配对、每次尝试和场景门槛审计 |
| `.github/workflows/baseline.yml` | Windows Python3.12回归、资产验证、历史与当前证据审计 |

核心链路：一次scene reset → 观测 → 估计pose → 候选生成/宽度筛选 → approach、lift、place预检 → PRE_GRASP → APPROACH → close → LIFT → 保持验证 → TRANSFER → LOWER → open → RETREAT → 放置验证 → 外层邻物保护验证。

位姿采用 `T_A_B`，将B系坐标映射到A系；长度m、角度rad、力N。相对持物变换 `T_site_object = inverse(T_world_site) @ T_world_object`。姿态估计、IK、路径、控制和结果判定职责应继续分离。

当前绕障是有限净空/侧通道与RRT组合，九个IK初值和RRT180迭代均有预算。路径约每0.015 rad关节增量做离散检查；不构成连续碰撞安全证明。

## 6. 成功、失败与恢复的精确定义

### 6.1 成功门槛

| 条件 | v2.0.0使用的门槛 |
|---|---|
| 提升保持 | 1秒采样中最小目标高度严格高于原episode初始高度+0.08 m |
| 双指接触 | 保持采样中双侧接触比例≥0.95 |
| 放置位置 | 最终XY到配置目标中心距离严格小于0.055 m |
| 释放/支撑 | 无夹爪接触，且有桌面支撑接触 |
| 稳定 | 松爪退回后静置1秒，最终线速度严格小于0.02 m/s |
| 邻物保护 | 自初始化静置后起，全程邻物最大三维平移≤0.02 m |
| 不安全接触 | 监测到的不安全接触步数为0；机器人-邻物穿入深度>0.5 mm或目标-邻物/障碍穿入>1 mm记为不安全 |
| 目标穿入 | 对邻物/固定障碍最大穿入≤0.001 m |
| 执行配置 | 夹爪actuator力上限40 N；关节速度0.5 rad/s、加速度2 rad/s² |

邻物旋转和表面损伤没有独立门槛；邻物平移基准是0.8秒静置后的姿态，初始化静置期不计入位移监测。模型接触允许的小穿入阈值不等于现实刚体安全距离。

不要只看 `lift_success` 或 `place_success`：目标放置可能成功，但外层邻物保护失败，episode最终仍失败。正式分母是物理episode数，不能把第二次尝试计为另一独立新场景。恢复成功还要满足最初场景的提升高度门槛，防止重试降低评价标准。

### 6.2 恢复策略和边界

首次/后续尝试仅第一次reset。`PERCEPTION_FAIL` 或未执行机械臂阶段的 `PLANNING_FAIL` 可重新观测；`GRASP_FAIL` 可开爪、规划上退0.12 m、回home、静置0.4秒，再跳过先前候选。其他失败和不安全退回终止。

`FeedbackController` 在trajectory执行期间监测双指接触；连续失联40 ms产生 `SLIP_DETECTED`。双侧接触但最小法向力<4 N时，按0.02 N步进提高受限预载至32 N，actuator仍受40 N上限约束。它不是完整的触觉重抓或所有任务阶段的安全监督器：例如提升保持由 `verify_lift` 另行采样判定。

这些机制已有开发/回归案例；正式270次中，没有首次失败被恢复为成功。不能将测试覆盖表述为正式恢复成功率提升。

## 7. 正式实验结果及解释

根种子20261601，目标按随机排列分块均衡。各组相同trial index使用：scene seed=根种子+1000+i，sensor seed=根种子+100000+i，planner seed=根种子+200000+i。三组clutter方法的目标和静置后所有物体姿态精确配对。

| 条件 | 首次/最终成功 | 完整成功率 | 95% Wilson区间 | 平均观测帧 | 平均总墙钟时间 |
|---|---:|---:|---:|---:|---:|
| isolated_active | 29/30 → 29/30 | 96.7% | 83.3%–99.4% | 24.0 | 3.57秒 |
| obstacles_active | 30/30 → 30/30 | 100.0% | 88.6%–100.0% | 24.0 | 27.52秒 |
| fixed_clutter | 50/60 → 50/60 | 83.3% | 72.0%–90.7% | 64.0 | 10.27秒 |
| active_clutter | 52/60 → 52/60 | 86.7% | 75.8%–93.1% | 23.7 | 10.11秒 |
| recovery_clutter | 52/60 → 52/60 | 86.7% | 75.8%–93.1% | 26.7 | 12.23秒 |
| dense_recovery | 25/30 → 25/30 | 83.3% | 66.4%–92.7% | 28.0 | 14.42秒 |


前三种clutter策略的首次成功数与最终成功数相同。fixed→active恢复2个失败、退化0个；active→recovery恢复0个、退化0个。recovery_clutter有8个episode使用第二次尝试，最终仍失败。

三个clutter方法是物理场景配对，不是逐像素相同观测：fixed和active视角调度不同。recovery同时增加反馈与重试，因此不是单独反馈收益的消融。其他三组还改变环境难度，不能将条件间全部差异归于算法。

| 目标 | isolated | obstacles | fixed clutter | active clutter | recovery clutter | dense recovery |
|---|---:|---:|---:|---:|---:|---:|
| foam_brick | 10/10 | 10/10 | 12/20 | 12/20 | 12/20 | 5/10 |
| gelatin_box | 10/10 | 10/10 | 18/20 | 20/20 | 20/20 | 10/10 |
| pudding_box | 9/10 | 10/10 | 20/20 | 20/20 | 20/20 | 10/10 |


| 条件 | 全部最终失败 |
|---|---|
| isolated_active | PLACE_FAIL=1 |
| obstacles_active | 无 |
| fixed_clutter | PLACE_FAIL=1, PLANNING_FAIL=8, CLUTTER_DISTURBANCE_FAIL=1 |
| active_clutter | PLANNING_FAIL=8 |
| recovery_clutter | PLANNING_FAIL=8 |
| dense_recovery | PLANNING_FAIL=5 |


Wilson区间表示此有限样本比例的不确定性；30/30不能推断泛化成功率必为100%。正式计时来自并发本地运行，且 `planning_time_s`、`execution_time_s`不是完整总时间分解：观测、夹爪动作、保持验证、恢复退回等开销可能体现在total中。当前不能据此宣称真实机器人实时性能。

## 8. 证据格式、复现与修改后的审计

每组目录中一份 `summary_*.json`、一份 `trials_*.jsonl`和简化CSV。summary保存版本、源码指纹、依赖/资产commit、scene/mode、传感器/物理配置、成功/失败统计、分物体和时间。

JSONL才是完整接手依据，重点字段：`trial_id`、`object_id`、三个seed、`spawn_pose`、`estimated_pose`、`candidate_rejections`、`executed_stages`、`attempts`、`recovery_actions`、`first_attempt_success`、`attempt_count`、`observed_frames`、`planner_stats`、`feedback`、`scene_metrics`、`failure_stage`和物理验证值。有些失败发生较早，后续物理字段不存在；分析时不能假设每条记录都有完整成功字段。

`scene_metrics.initial_scene`保存活动对象静置后姿态；`scene_resets`为环境累计值，`reset_count`才是本episode reset次数。CSV不保留全部nested信息，不适合单独证明恢复/邻物门槛。

正式engine指纹覆盖 `clutter_main.py` 与 `robot_manipulation`根目录全部`.py`，文件名和LF规范化内容一起计算。它没有覆盖scripts/tests/依赖二进制；所以实验协议、依赖和资产锁也必须保留。

v2正式engine SHA-256：`c2e20bc4bacde448c68abe5ee416171fafefcc6e2b9a5d5a0aa74cc47bb8aa5d`。

```powershell
# 旧证据对旧标签：修改当前engine后仍可审计历史事实
.\.venv\Scripts\python.exe scripts/check_v2_evidence.py --source-ref v2.0.0
.\.venv\Scripts\python.exe scripts/check_reliability_evidence.py --source-ref v1.1.0
.\.venv\Scripts\python.exe scripts/check_obstacle_evidence.py --source-ref v1.2.0
.\.venv\Scripts\python.exe scripts/check_obstacle_reliability.py --source-ref v1.3.0
.\.venv\Scripts\python.exe scripts/check_sensing_evidence.py --source-ref v1.4.0

# 完整重跑270次；必须新目录，运行中不要修改engine
.\.venv\Scripts\python.exe scripts/benchmark_v2.py --output outputs/v2_reproduction
.\.venv\Scripts\python.exe scripts/check_v2_evidence.py --folder outputs/v2_reproduction
```

运行器每组启动前检查指纹，不能代替全程源码隔离；组员同时开发时应使用独立checkout/worktree冻结实验。运行器会产生时间戳文件；同一目录重跑会有多份summary，审计要求每组唯一文件，因此需要新的输出目录。

现有审计脚本针对20261601和固定270次协议写有硬性校验。`benchmark_v2.py --seed 新值`可以生成新实验，但不能直接套用旧审计宣称通过；后续应为新版本明确种子、组数/样本数并更新对应审计。不要把新结果覆盖进 `docs/validation/v2.0.0`。

### 8.1 优先复现的失败

active/recovery三干扰物共同失败trial：8、10、14、17、23、36、51、52，均foam_brick、PLANNING_FAIL。dense失败为8、10、14、17、23，同样类别和阶段。fixed还有gelatin_box trial3的PLACE_FAIL及trial18的CLUTTER_DISTURBANCE_FAIL。

严格复现原实验前缀的命令如下，包含前面成功与失败，日志各用独立目录：

```powershell
.\.venv\Scripts\python.exe clutter_main.py --headless --scene clutter --mode active --seed 20261601 --trials 8 --output outputs/replay_active_prefix8
.\.venv\Scripts\python.exe clutter_main.py --headless --scene dense --mode recovery --seed 20261601 --trials 8 --output outputs/replay_dense_prefix8
```

若为快速调试只跑一个trial，可根据原trial i设置CLI seed为20261601+i-1、指定原object并跑一次，使三类seed对齐。**这种单例快捷复现仍须比对原JSONL的全部初始物体pose后再作为配对证据**，不能只凭相同seed宣称等价。计数器和日志trial_id会变化。

## 9. 已知问题和待确认事项

| 优先级 | 已知事实 | 证据/影响与建议入口 |
|---|---|---|
| P0 | foam_brick规划拒绝集中出现 | 三干扰物12/20、dense5/10。trial8仅两个候选，均报九个IK初值不收敛或静态碰撞拒绝。错误信息合并了两类原因；先分解诊断，不能断言物理不可行 |
| P1 | 正式恢复没有增加成功数 | 八个三干扰物失败重观测后仍失败；相同类别/有限候选的几何问题未解决。需改变候选/规划机制后再验证恢复收益 |
| P1 | 目标分割是理想掩码，光学是合成代理 | clutter透明目标识别和真实折射尚待开发，不能作为现成能力交付 |
| P1 | 对场景/地图有真值依赖 | 位姿估计无oracle回退，但碰撞/持物/降低仍读状态；真实部署需要地图和不确定性管理 |
| P2 | 普通GUI目标标记与v2配置不一致 | environment.py把`place_target` site写为(.48,.22)，v2实际判定(.48,.30)。record_clutter_demo.py单独修正了标记。后续应统一由Config生成，仅改显示，不改任务门槛 |
| P2 | 报告/录制工具不完全通用 | build_v2_report.py固定旧证据目录/版本；record_clutter_demo.py固定开发成功seed，且第二次观测默认预算不同于CLI。不能用演示替代正式评估 |
| P2 | README后部有历史baseline限制段落 | “oracle、单物体、不绕障”等适用于旧baseline入口，不能脱离章节用于概括v2。接手时按入口/版本解释，后续可明确重命名历史章节 |
| P2 | 批量审计与协议硬编码 | 新seed、扩展对象或新增组需配套新协议/审计，而非修改旧数据迎合断言 |

当前代码没有动态障碍、堆叠物体重排、未知类别透明识别、材质标定、完整触觉闭环或真实机器人执行。这些均是后续设计方向，不是已经实现但尚未开启的开关。

## 10. 后续优化顺序和验收建议

以下为组员任务建议，不是已完成开发或新的课程强制要求。首要目标是定位失败与保持评价诚实，再增加复杂度。

### A. 失败诊断与foam_brick抓取/规划（最高优先）

先拆分IK不收敛、末端姿态误差、关节边界、机器人-障碍/邻物碰撞、approach边失败、lift预检和place预检。记录每个候选的pose/宽度、各IK seed、碰撞geom/深度以及preview/execution scope。

候选方向可研究多抓取高度、中心附近接触点、更多可行入射姿态、场景感知候选排序；路径方向可研究多目标IK、邻物净空代价或更有界的搜索。不得为成功放宽夹爪宽度/力/碰撞门槛，也不能假设增加候选必然改善。

建议验收：旧失败集上说明恢复与退化数量；再冻结源码，在新种子配对实验中同时报告总成功率、各目标、规划时间/预算和邻物扰动。90%可作为小组后续目标，但预先约定样本数、场景范围和置信区间；不以训练/调参用失败集作为独立泛化结果。

### B. 有实际收益的有限恢复

将恢复与失败原因关联：几何不可行时只重观测通常不足；可在有限预算内换接近方向/抓取候选，或安全退回后重规划。先用可控注入案例验证不reset、不偷改高度，再做独立完整episode评估。

建议至少比较普通控制、仅反馈、仅恢复、反馈+恢复；每组记录首次成功、恢复后成功、平均尝试/帧数/总时间、恢复动作和恢复引发的不安全接触。对slip或碰撞后的继续执行必须有明确物理安全条件，不能简单忽略失败。

### C. 感知可靠性与减少理想条件

先引入更强固定遮挡、相关缺失、离群深度、标定偏差和感知不确定性；校验主动置信度是否拒绝错误稳定估计。之后将理想掩码替换为可评估的分割/目标指定接口，分别报告识别、估计和执行误差。

如果选择真实透明数据集，先明确数据/材质/标注来源、许可、测量方式与仿真接口；只有验证过真实数据或折射模型后才升级“透明感知”结论。新数据集或方案目前没有指定，需组内讨论与原CA要求核对。

### D. 场景复杂度扩展

在当前3/5邻物体系稳定后，再逐层增加更窄间隙、位置随机范围、障碍布局、目标形状、接触/堆叠或运动障碍。若允许先移开邻物，必须新增任务定义与重排预算；与当前“邻物全程≤20 mm”保护目标可能冲突，应作为独立条件报告。

先冻结难度分层和成功条件再跑对照，避免为了提高指标把物体移远、缩小网格、禁用碰撞、提高摩擦或删失败。

### E. 展示、工程和最终报告

修正Config驱动的目标显示，统一视频/CLI配置和日志输出，给报告工具增加版本/证据路径参数；这些是低风险工程任务，但修改engine仍会产生新指纹。最后整合贡献、算法图、全部结果、失败分析、局限、引用、复现步骤和组员实际信息。展示视频应注明演示seed并提供成功与典型失败，不能只凭单条成功视频概括系统性能。

## 11. 建议组内分工与接口

| 工作流 | 主要负责模块 | 每阶段应交付 |
|---|---|---|
| 抓取/规划组员 | grasp、IK、robust/clutter planning | 原因诊断、候选/搜索改动、配对结果与耗时 |
| 感知组员 | active/depth sensing、分割接口 | 观测模型与假设、估计误差/拒绝率、帧预算 |
| 控制/恢复组员 | control、feedback、recovery | 物理接触与恢复状态机、预算、无reset证明、消融 |
| 实验/整合组员 | benchmark、审计、CI、报告/视频 | 冻结协议、完整JSONL、统计、报告、可运行交付 |

以上是工作流建议，可由同一成员兼任，不代表实际人员分配。共享接口由组内维护人统一确认：observer返回估计状态及metrics；planner返回trajectory并抛StageFailure；controller只通过物理执行；evaluation保持独立。合并涉及公共pipeline/config之前先沟通，以免多人同时改成功口径。

## 12. 验证清单与Git协作规则

### 12.1 本地回归

```powershell
.\.venv\Scripts\python.exe tests/test_asset_setup.py
.\.venv\Scripts\python.exe tests/test_baseline.py
.\.venv\Scripts\python.exe tests/test_dataset.py
.\.venv\Scripts\python.exe tests/test_obstacle_planning.py
.\.venv\Scripts\python.exe tests/test_robust_obstacles.py
.\.venv\Scripts\python.exe tests/test_depth_sensing.py
.\.venv\Scripts\python.exe tests/test_active_sensing.py
.\.venv\Scripts\python.exe tests/test_recovery.py
.\.venv\Scripts\python.exe tests/test_clutter.py
```

v2版本上述9个测试文件共34项。测试采用真实仿真案例和关键拒绝/状态保护检查，不是270次正式评估的替代品。CI还做历史证据与当前证据审计、cube及真实网格smoke。文档改动通常只需对应事实/链接检查；行为变化应跑相关回归和物理验证，完整阶段再跑CI。

### 12.2 源码变更与旧证据

当前workflow最后一步直接审计当前engine与旧v2证据。组员修改engine后，这一步因指纹不符失败是**合理保护**，不是数据坏了。新功能PR应把历史v2审计改为 `--source-ref v2.0.0`，同时新增新版本证据和对应审计；不能只关闭检查或把旧summary的hash改成新hash。

### 12.3 分支与提交

先检查 `git status`，不覆盖其他组员改动。遵循 `CONTRIBUTING.md`，功能使用 `feature/<主题>`，修复使用 `fix/<主题>`；已有自动开发工具可能使用自己的分支前缀，关键是保持独立分支和PR。不要多人对同一工作目录同时checkout或跑正式冻结实验。

完成一个有意义阶段后检查diff、运行相关验证、更新README/PROGRESS/CHANGELOG、提交推送、创建PR。PR说明具体问题、最终行为、证据和局限，通过CI再合并。不要频繁为小改动新建版本；不要force push main或修改v2.0.0标签/历史结果。

F盘若报dubious ownership，用具体目录例外：

```powershell
git -c safe.directory='F:/NUS/Semester I/EE5110/Segment C/CA' status
```

不可配置全局 `safe.directory=*`。其他机器应使用自己的真实项目路径。每名组员使用自己的GitHub认证；本机缓存授权、`.tools`私有辅助脚本与凭据不是交接依赖，也不应复制给组员。

不得提交 `.venv`、`.idea`、凭据、原始课程附件、下载机器人网格或日常全部输出。资产锁/来源纳入Git；下载模型由setup重建。正式证据只精选必要完整实验纳入 `docs/validation/<新版本>`，相关实验内部保留全部失败。

## 13. 报告、视频、打包与常见问题

生成报告：`scripts/build_v2_report.py`依赖reportlab，未列入核心requirements；目前固定读取旧v2目录并写旧报告，因此**新版本不要直接运行来覆盖历史报告**。先参数化或另建新脚本，逐页检查排版并核对数据。

录制需要OpenGL和 `requirements-video.txt` 中依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-video.txt
.\.venv\Scripts\python.exe clutter_main.py --headless --scene dense --object foam_brick --seed 45 --trials 1 --video outputs/new_demo.mp4 --output outputs/new_demo_logs
```

`--headless`仅关闭交互viewer；视频仍需渲染，不代表无GPU/OpenGL要求。固定开发演示重录工具 `scripts/record_clutter_demo.py`会覆盖旧发布视频/图片，后续应先改输出路径。旧演示不计入270次分母。

打包工具 `scripts/package_submission.py --version 2.0.0`使用allowlist，包含模型和许可证，不包含Git历史、环境和凭据。新版本需扩展版本映射、报告/视频文件名，避免覆盖旧ZIP。打包后做CRC/路径检查，解压到独立目录运行证据审计和实际任务；报告和ZIP完成不等于程序被验证。

| 症状 | 处理方式 |
|---|---|
| 找不到资产 | 确认setup脚本完成、lock校验通过；不能拿不同commit模型替代 |
| 缺mujoco/numpy或版本不符 | 确认解释器是项目.venv；按固定requirements安装 |
| GUI看似放在错误绿色区 | 核对config.place_xy与日志；已知旧site显示问题见第9节 |
| 运行结束返回0但有失败 | 默认退出码不代表成功，查看summary；严格smoke加require-all-success |
| 证据源码不匹配 | 检查是否修改engine；旧结果对旧tag审计，新结果独立版本，不篡改指纹 |
| 审计发现多份summary | 用新的实验目录，不删失败记录来凑唯一结果 |
| 历史审计找不到tag | Git克隆并fetch tags；离线ZIP无历史Git |
| 视频黑屏/渲染失败 | 先确认物理headless正常，再排查OpenGL/录制依赖；不要因此改物理模型 |

## 14. 组员接收与最终提交核对

接手成员可逐项记录实际完成日期/结果，不预填“通过”：

- [ ] 已取得仓库及v2.0.0标签，理解本文是发布后的文档补充。
- [ ] 已建立Python3.12 `.venv`，资产commit/hash与锁文件一致。
- [ ] 已运行当前/历史证据审计，知道标签与源码指纹的关系。
- [ ] 已跑通dense seed45物理案例，并查看完整summary/JSONL。
- [ ] 已复现至少一个规划失败并比对初始场景，区分已知原因与猜测。
- [ ] 已确定个人任务、接口、独立分支和验收协议。
- [ ] 后续结果将保留全部失败、分目标数据、首次/最终成功和扰动门槛。
- [ ] 最终报告将明确透明代理、掩码、真值地图、时间与场景范围。
- [ ] 原始CA中的提交格式、截止时间、视频/页数/成员信息由小组自行核对。
- [ ] 第三方模型/数据归属与许可保留；公开项目不代表模型许可可被忽略。

后续优化由接手组员开展。本文交接了稳定基线、可复现实验和已知问题，不将任何建议方案或目标成功率写成已完成结果。
