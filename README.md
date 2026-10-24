# EE5110 Segment C：机器人抓取项目与完整文件导航

本项目使用 **MuJoCo 3.15.0、Python 3.12、Franka Panda 机械臂**。包含公开 YCB 数据集的基础抓取流水线，以及密集遮挡、软体/铰接、未见形状、力反馈、故障恢复、受损感知六类独立拓展实验。

当前完整交付分支：[`feature/demo-materials-and-viewer`](https://github.com/m13961023616-pixel/EE5110-SegC/tree/feature/demo-materials-and-viewer)。本分支包含源码、模型/纹理及许可证、报告、视频、提交 ZIP、15 段剪辑素材和原始实验/录制输出。**下载时请选择此分支，不能用旧 main 代替。**

## 先按用途找文件

| 想做什么 | 打开哪个文件 |
|---|---|
| 打开交互演示界面 | 双击 [`OPEN_DEMO.cmd`](OPEN_DEMO.cmd)，输入菜单序号并按 Enter。 |
| 自己剪视频 | [`deliverables/editing_materials/`](deliverables/editing_materials/)；整体下载用 [`editing_materials.zip`](deliverables/editing_materials.zip)。 |
| 了解每段视频的内容和界面操作 | [`docs/DEMO_EDITING_GUIDE.md`](docs/DEMO_EDITING_GUIDE.md)。 |
| 看带介绍的拓展成片 | [`deliverables/explorations_v3.0.0.mp4`](deliverables/explorations_v3.0.0.mp4)，约 3 分 33 秒。 |
| 看最新拓展报告 | [`output/pdf/exploration_report_v3.0.0.pdf`](output/pdf/exploration_report_v3.0.0.pdf)，10 页。 |
| 看上一阶段基线报告 | [`output/pdf/final_report_v2.1.0.pdf`](output/pdf/final_report_v2.1.0.pdf)，6 页。 |
| 找当时验证过的提交包 | [`deliverables/README.md`](deliverables/README.md)，解释两个版本 ZIP 的范围。 |
| 跑全部拓展、了解假设和限制 | [`docs/EXPLORATION_HANDOVER.md`](docs/EXPLORATION_HANDOVER.md)。 |
| 看每个 Python 文件的作用 | [`docs/FILE_GUIDE.md`](docs/FILE_GUIDE.md)。 |
| 找所有上传文件及其用途、大小、哈希 | [`PROJECT_FILES.json`](PROJECT_FILES.json)，逐文件完整索引。 |
| 看旧版本记录 | [`README_HISTORY.md`](README_HISTORY.md)、[`CHANGELOG.md`](CHANGELOG.md)、[`PROGRESS.md`](PROGRESS.md)。 |

## 下载后怎样运行

可以在此分支点 **Code → Download ZIP** 并解压，或克隆：

```powershell
git clone --branch feature/demo-materials-and-viewer https://github.com/m13961023616-pixel/EE5110-SegC.git
Set-Location EE5110-SegC
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/setup_assets.py
.\.venv\Scripts\python.exe scripts/setup_ycb.py
.\OPEN_DEMO.cmd
```

模型已经随分支提供；两个 setup 脚本会优先校验已有文件，缺失时才下载。Python 和依赖仍需要在新电脑安装；`.venv` 不能直接从别的电脑搬过来。本机已有 `.venv` 时直接双击启动，不必重复创建。

演示会自动控制机械臂；空格暂停/继续，左键拖动旋转，右键拖动平移，滚轮缩放。完成后画面保持，关闭窗口退出；重新演示请重开菜单。批量实验使用下面的无界面入口。

```powershell
# 基础公开数据集抓放
.\.venv\Scripts\python.exe main.py --headless --balanced --task place --trials 6 --seed 43
# 拓展单例；其他 case 名称见下方和交付指南
.\.venv\Scripts\python.exe exploration_main.py --case soft_adaptive --trials 1 --seed 43
.\.venv\Scripts\python.exe exploration_main.py --case recovery_retry --trials 1 --seed 43
# 验证所有下载文件（不需要 Git，仅需 Python 标准库）
.\.venv\Scripts\python.exe scripts/build_file_inventory.py --verify-files
```

录制视频需额外安装 `requirements-video.txt`；生成报告/图需安装 `requirements-report.txt`。现成 MP4/PDF/ZIP 可直接查看，无需先装这些生成依赖。

## 根目录各文件的作用

| 文件 | 作用 |
|---|---|
| [`OPEN_DEMO.cmd`](OPEN_DEMO.cmd) | Windows 双击启动菜单，调用项目虚拟环境。 |
| [`打开演示界面.cmd`](打开演示界面.cmd)、[`开始使用.md`](开始使用.md) | 中文双击入口和最短上手指引。 |
| [`demo_viewer.py`](demo_viewer.py) | 基础及拓展的交互界面；支持暂停、最多 60 Hz 显示刷新、结束后停留。 |
| [`main.py`](main.py) | 基础流水线：随机 YCB 物体、抓取候选、IK/碰撞检查、物理抓取/放置及评估；不加 `--headless` 可显示界面。 |
| [`challenge_main.py`](challenge_main.py) | 早期障碍环境与避障规划实验入口。 |
| [`sensing_main.py`](sensing_main.py) | 早期透明外观代理及合成深度感知对照入口。 |
| [`clutter_main.py`](clutter_main.py) | v2.1 动态 YCB 邻物、复合障碍、局部抓取及有界恢复入口。 |
| [`exploration_main.py`](exploration_main.py) | v3.0 全部 14 个拓展条件的批量入口，默认无界面，输出逐次日志和汇总。 |
| [`RUN_PROJECT.ps1`](RUN_PROJECT.ps1) | 原有 clutter/dense 等场景的 PowerShell 启动脚本。 |
| [`requirements.txt`](requirements.txt) | 核心物理仿真与数值计算依赖版本。 |
| [`requirements-video.txt`](requirements-video.txt) | 录制/处理视频所需依赖。 |
| [`requirements-report.txt`](requirements-report.txt) | 报告生成、PDF 检查和标准绘图依赖。 |
| [`PROJECT_FILES.json`](PROJECT_FILES.json) | 除索引自身外的全量上传文件：路径、用途、字节数和 SHA-256；文本按声明的 LF 规则校验。 |
| [`README_HISTORY.md`](README_HISTORY.md) | 原 README 的阶段历史，保留原有结果和限制；上传状态以本文件为准。 |
| [`CHANGELOG.md`](CHANGELOG.md) | 按阶段记录实际改动。 |
| [`PROGRESS.md`](PROGRESS.md) | 已完成工作、验证结果和已知限制。 |
| [`CONTRIBUTING.md`](CONTRIBUTING.md)、[`AGENTS.md`](AGENTS.md) | 人工/代理协作约定、物理真实性和提交规范。 |
| [`.gitignore`](.gitignore) | 排除环境、凭据、缓存和临时解压副本。 |
| [`.gitattributes`](.gitattributes) | Git 换行/二进制规则；锁定模型、视频、ZIP 和原始素材按原始字节保留。 |
| [`.github/workflows/baseline.yml`](.github/workflows/baseline.yml) | 推送/PR 后自动验证模型、物理机制、历史及当前证据。 |
| [`.github/pull_request_template.md`](.github/pull_request_template.md) | 提交 PR 时填写问题、改动和验证结果的模板。 |

## 各目录的作用

| 目录 | 内容 |
|---|---|
| [`robot_manipulation/`](robot_manipulation/) | 共用的基线环境、模型读取、观测、抓取生成、IK/路径规划、控制、恢复和结果判定。 |
| [`exploration/`](exploration/) | 新拓展模型、无 CAD 抓取观测、接触反馈、受控故障恢复、冻结实验定义和源码指纹。 |
| [`scripts/`](scripts/) | 下载/校验模型、批量实验、证据审计、报告/视频生成、素材导出、ZIP 及文件索引工具。 |
| [`tests/`](tests/) | 有意义的物理、失败拒绝、状态隔离与证据防伪测试，现有 49 项。 |
| [`assets/`](assets/) | 固定版本的 Panda/YCB 模型、网格、纹理、许可证和哈希锁文件；共 122 个模型目录文件。 |
| [`deliverables/`](deliverables/) | 合成视频、历史提交 ZIP、15 段独立原速素材及其打包；逐项说明见该目录 README。 |
| [`output/pdf/`](output/pdf/) | 两份续作英文报告。 |
| [`docs/report/`](docs/report/) | 更早版本的英文报告，保留历史研究范围。 |
| [`docs/images/`](docs/images/) | 实际场景截图、成功率/力/应变/铰接轨迹和点云图。 |
| [`docs/validation/`](docs/validation/) | 分版本整理的实验协议、完整逐次结果、汇总与配对比较。 |
| [`outputs/`](outputs/) | 原始实验运行和原始录像、中间片、开发诊断；含旧失败，用途见该目录 README。 |

每个源码/工具/测试的中文逐文件说明，以及模型文件和日志格式的解释，见 [文件详解](docs/FILE_GUIDE.md)。`PROJECT_FILES.json` 还列出每一个模型子文件、视频和日志的用途与校验信息。

## 实验入口与结果怎样对应

| 研究方向 | `exploration_main.py --case` | 正式结果 |
|---|---|---|
| 密集遮挡 | `crowding_single` / `crowding_active` | 5/6 / 3/6 |
| 软体 | `soft_fixed` / `soft_adaptive` | 2/6 / 6/6 |
| 被动铰接物 | `articulated` | 6/6 |
| 未见形状 | `novel_prior` / `novel_points` | 11/12 / 11/12 |
| 力反馈 | `force_fixed` / `force_adaptive` | 10/12 / 12/12 |
| 受控故障恢复 | `recovery_single` / `recovery_retry` | 0/6 / 6/6 |
| 受损感知 | `sensor_single` / `sensor_raw_fusion` / `sensor_robust` | 6/12 / 1/12 / 9/12 |

v3.0 为独立的 14 条件、126 次新物理实验，原始/精选副本不能重复计数；v2.1 的 180 次配对候选研究独立保留。每组仅 6 或 12 次，七项配对比较经多重校正后均未达到 0.05。主动遮挡退化、形状对照持平、融合失败和楔形滑落均保留，不宣称任意场景 100% 成功。

软体为实际弹性 flex，铰接件保持被动转轴，但并未实现主动开盖；点云抓取估计无 CAD 输入，规划/搬运仍使用仿真几何。合成深度误差不是玻璃折射模型，受控故障恢复也不是自然故障通用恢复率。小组姓名、学号及实际个人贡献需要如实填写。

## 验证与重新生成

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/check_completion_evidence.py
.\.venv\Scripts\python.exe scripts/check_exploration_evidence.py
.\.venv\Scripts\python.exe scripts/prepare_editing_materials.py
```

已提供原始录制输入，因此最后一条可从分支现有素材重新导出全部 15 段，并完整解码、打包校验。重新采样使用 `scripts/benchmark_exploration.py --output outputs/new_run`，不要混入已冻结的目录。

维护文件索引时，先暂存要上传的文件，再运行 `python scripts/build_file_inventory.py` 并暂存生成的 `PROJECT_FILES.json`；`--check` 检查索引是否对应 Git 暂存区，`--verify-files` 检查实际下载的文件。索引自身不列入自身哈希。

本分支没有上传 `.venv`、Python 安装目录、本机工具/凭据、缓存、临时解压的重复副本和原始课程附件。模型/数据属于第三方，原许可证和归属说明保留，见 [`docs/ASSET_ATTRIBUTION.md`](docs/ASSET_ATTRIBUTION.md)。
