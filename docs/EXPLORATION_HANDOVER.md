# 六类拓展实验运行与交付说明（v3.0.0）

课程列举的六类具体拓展方向均已实现并完成独立实验。这里的“完成”指有可运行机制、物理执行、对照/可行性证据、失败记录和报告；不代表解决了整个研究领域，也不代表所有复杂条件组合后均能成功。

## 交付物

- 英文报告：`output/pdf/exploration_report_v3.0.0.pdf`，包括全部条件、失败分析、统计限制和贡献边界。
- 七段物理演示组成的视频：`deliverables/explorations_v3.0.0.mp4`，字幕说明机制和限制，动作以标明的 2 倍速播放。
- 完整提交包：`deliverables/EE5110SegC_submission_v3.0.0.zip`，包含源码、测试、报告、视频、锁定模型及许可证、实验记录和 SHA-256 清单。
- 新实验记录：`docs/validation/v3.0.0`，14 组、126 次；开发演示单独放在 `demo/`，不进入正式分母。
- 原有基线说明与 180 次实验保留在 [v2.1 交付说明](FINAL_HANDOVER.md)，旧报告也放入新 ZIP。

按用户后续要求，完整分支现已纳入视频、ZIP、模型、原始录制输入和代码/证据/报告，目录用途见根 README。历史 submission ZIP 保留原快照；最新交互菜单和文件导航以当前分支源码为准。组员姓名、学号和实际个人贡献需要按真实情况填写。

## 环境与最快复现

在项目根目录打开 PowerShell。使用 Python 3.12；已配置的本机环境为 Python 3.12.15、MuJoCo 3.15.0、NumPy 2.5.3。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/setup_assets.py
.\.venv\Scripts\python.exe scripts/setup_ycb.py
.\.venv\Scripts\python.exe exploration_main.py --case soft_adaptive --trials 1 --seed 43 --require-all-success
```

本机 `.venv` 已建立，无需重复创建。ZIP 自带校验过的模型，setup 命令会先验证已有文件。ZIP 不包含 Python 或离线依赖轮子；全新机器仍需先安装 Python 和依赖。

新入口默认无图形界面。逐项运行下表命令时，可加 `--trials 1 --seed 43 --video outputs/example.mp4 --snapshot`，得到实际执行录像和抓取/提升/放置截图；录像需要安装 `requirements-video.txt`。旧基线 GUI 仍通过 `main.py`、`clutter_main.py` 或 `RUN_PROJECT.ps1` 启动。

| 方向 | `exploration_main.py --case` 后的参数 | 正式结果 |
|---|---|---|
| 密集遮挡 | `crowding_single` / `crowding_active` | 5/6 / 3/6 |
| 可变形物体 | `soft_fixed` / `soft_adaptive` | 2/6 / 6/6 |
| 铰接物体 | `articulated` | 6/6 |
| 未见不规则形状 | `novel_prior` / `novel_points` | 11/12 / 11/12 |
| 力/接触反馈 | `force_fixed` / `force_adaptive` | 10/12 / 12/12 |
| 故障检测与恢复 | `recovery_single` / `recovery_retry` | 0/6 / 6/6 |
| 更现实的受损感知 | `sensor_single` / `sensor_raw_fusion` / `sensor_robust` | 6/12 / 1/12 / 9/12 |

## 实现和边界

1. 密集遮挡：五个有重力和碰撞的 YCB 邻物、缩小的间隙、挡板、两根柱子和实体侧屏。每次场景都有低于 50% 可见率的视角。仍使用已知目标和理想实例掩码；没有宣称完成任意堆叠或真实杂乱分割。主动策略退化的两次 PLACE_FAIL 原样保留。
2. 软体和铰接：真正的 3D 弹性 flex，27 顶点、24 约化变形自由度；另一模型有受重力和接触作用的被动转轴。没有机器人与物体之间的 weld 或粘附。软体材料研究使用仿真几何，规划时对当前形状采用刚性搬运近似；铰接任务是整件抓放，没有主动开盖。
3. 未见形状：随机尺寸的锥缩、非对称、缺口和楔形实例；楔形未参与早期调参。观测器从无遮挡实例标签的完整点云提取几何，使用事先固定的工作区提示和已知桌面，没有 CAD 输入；碰撞检查和搬运中心仍使用仿真状态。两方法同为 11/12，不能声称成功率提升。
4. 力控制：实际修改模型质量、摩擦和指令延迟；测量真实接触法向力并闭环调节。力上限和失联停止保留。软体反馈组的平均峰值应变更高，不能解释为减小了变形。
5. 恢复：第一次夹爪闭合受到真实执行的指令故障，宽于目标，缺少双指接触；检测后张开、检查撤离/回位、重新观测并重抓。全程只初始化一次场景，目标没有瞬移。这是受控故障实验，不能代替自然故障频率或任意失败恢复率。
6. 感知/物理真实性：独立缺失、持续条带缺失、AR(1) 漂移、噪声、离群点、固定标定偏差、质量/摩擦/延迟随机化。稳健融合按不同数据包的体素支持度过滤。没有模拟真实玻璃折射，也没有实机或实时相机传输实验。

## 验证和生成

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/check_completion_evidence.py
.\.venv\Scripts\python.exe scripts/check_exploration_evidence.py
.\.venv\Scripts\python.exe scripts/benchmark_exploration.py --output outputs/new_exploration_run
.\.venv\Scripts\python.exe -m pip install -r requirements-video.txt -r requirements-report.txt
.\.venv\Scripts\python.exe scripts/record_exploration_demo.py
.\.venv\Scripts\python.exe scripts/build_exploration_figures.py
.\.venv\Scripts\python.exe scripts/build_exploration_report.py
.\.venv\Scripts\python.exe scripts/package_submission.py --version 3.0.0
.\.venv\Scripts\python.exe scripts/verify_submission.py --extract-to outputs/new_zip_verification
```

49 项测试覆盖原功能和新机制；新审计检查全部 126 次、源码指纹、配对初态/材料/首个受损数据包及物理成功门槛。独立 ZIP 验证会校验 CRC、全部文件哈希、模型及两套证据，并在新解压目录实际执行旧基线、软体释放和故障恢复。再次验证时使用新的空目录。

新代码位于 `exploration/`，没有修改 v2.1 引擎。冻结指纹覆盖新入口、旧引擎、实验驱动和审计；改动这些文件后必须重新采样，不能把旧日志改成新指纹。正式实验种子为 20261026，开发演示为 43。各方向是独立研究，不汇总成一个成功率；每组仅 6 或 12 次，七个配对检验经 Bonferroni 校正后均未达 0.05。
