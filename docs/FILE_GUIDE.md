# 各文件作用详解

总入口见 [根 README](../README.md)，完整路径/大小/哈希见 [PROJECT_FILES.json](../PROJECT_FILES.json)。这里按职责解释源码和数据；模型的重复网格、纹理和逐次日志按文件类型解释，索引则覆盖每一个实际文件。

## 源码与工具

### `robot_manipulation/`：共用基线引擎

| 文件 | 作用 |
|---|---|
| `__init__.py` | 定义 Python 包。 |
| `config.py` | 集中定义步长、随机摆放范围、夹爪力、提升/保持/放置门槛和初始关节位置。 |
| `environment.py` | 构建 Panda、桌面、目标、相机与放置区；管理模型标识、初始化和实际物理步进。 |
| `dataset.py` | 读取六种 YCB 网格，适配模型/纹理和碰撞几何，记录尺寸、质量及惯量近似。 |
| `transforms.py` | 位姿矩阵、旋转误差及坐标转换；采用 `T_A_B` 将 B 系坐标映射到 A 系。 |
| `perception.py` | 基线目标状态/几何接口，基线使用仿真已知状态。 |
| `grasp.py` | 从估计几何生成候选抓取、预抓取、提升姿态、开口宽度和排序。 |
| `local_grasps.py` | 保留原候选前缀，最多增加 16 个倾斜/偏移候选以避开邻物。 |
| `planning.py` | 阻尼雅可比 IK、关节约束、路径采样碰撞检查及任务预检。 |
| `search.py` | 有限预算双向 RRT-Connect 路径搜索，由调用方提供碰撞检查。 |
| `obstacle_planning.py` | 有物理障碍时的绕行规划与持物碰撞检查。 |
| `robust_obstacles.py` | 夹爪对称姿态、不同搬运通道和可行放置中心候选。 |
| `clutter.py` | 同时存在的动态 YCB 邻物、复合障碍、邻物扰动与不安全接触指标。 |
| `clutter_planning.py` | 复杂障碍/邻物中的持物姿态与放置方向选择。 |
| `control.py` | 实际执行关节轨迹和夹爪命令，限制夹持力并检查碰撞/跟踪误差。 |
| `feedback.py` | 接触力反馈、执行器限制与持续失联停止。 |
| `depth_sensing.py` | 合成射线深度、缺失/噪声、已知盒形拟合；明确其光学简化。 |
| `active_sensing.py` | 有限多视角观测、几何置信度和有界观测预算。 |
| `recovery.py` | 同一物理场景内有限重试，保留首次/最终结果，不在尝试间重置。 |
| `pipeline.py` | 单次完整任务：观测→候选→规划→闭合→提升保持→搬运释放→判定。 |
| `evaluation.py` | 物理提升/放置判定、Wilson 区间、逐次日志与汇总。 |
| `video.py` | 从实际物理状态渲染并流式编码 MP4，带阶段标记。 |
| `visualization.py` | 离屏生成实际场景 PNG 截图。 |

### `exploration/`：六类具体拓展的独立实现

| 文件 | 作用 |
|---|---|
| `__init__.py` | 定义拓展包，保持旧引擎独立。 |
| `workcell.py` | 生成随机不规则刚体、被动铰接件和真实弹性 flex；管理材料/延迟、接触和应变指标。 |
| `crowding.py` | 更紧密的动态邻物、实体遮挡屏和初始可见率测量。 |
| `sensing.py` | 无实例标签/CAD 输入的前景点云组件、几何拟合、相关深度扰动和跨帧体素支持过滤。 |
| `manipulation.py` | 测量几何抓取候选、拓展规划、接触力闭环、实际部分闭合故障和安全撤离重试。 |
| `runner.py` | 创建每类场景，执行一次 episode，记录具体物理模型、种子和真值使用边界。 |
| `protocol.py` | 14 个冻结条件、配对关系及不放宽的物理成功门槛。 |
| `provenance.py` | 计算物理代码、实验驱动和审计定义的源码 SHA-256。 |

### `scripts/`：维护、实验和生成工具

| 文件 | 作用 |
|---|---|
| `setup_assets.py` | 校验/补下载锁定版本的 Panda 模型；已有有效文件不会重下。 |
| `setup_ycb.py` | 校验/补下载六个 YCB 物体的网格、纹理、碰撞部件和许可证。 |
| `download.py` | 下载的有限重试、错误处理与恢复机制。 |
| `benchmark_reliability.py` | v1.1 基础可靠性分组实验。 |
| `benchmark_obstacles.py` | v1.2 空场景/障碍场景的配对实验。 |
| `benchmark_obstacle_reliability.py` | v1.3 精确旧版本与改进规划的同场景比较。 |
| `benchmark_sensing.py` | v1.4 合成深度方法的冻结配对比较。 |
| `benchmark_v2.py` | v2.0 动态杂乱、主动观测和恢复的平衡实验。 |
| `benchmark_completion.py` | v2.1 原/局部候选在相同场景中的 180 次配对消融。 |
| `benchmark_exploration.py` | v3.0 14 条件、126 次拓展实验，先冻结协议再运行，保留全部失败。 |
| `check_reliability_evidence.py` | 审计 v1.1 完整样本、源码版本和成功门槛。 |
| `check_obstacle_evidence.py` | 审计 v1.2 障碍比较的场景配对与物理结果。 |
| `check_obstacle_reliability.py` | 审计 v1.3 精确版本与逐场景规划可靠性比较。 |
| `check_sensing_evidence.py` | 审计 v1.4 同场景感知和物理执行证据。 |
| `check_v2_evidence.py` | 审计 v2.0 全部尝试、动态邻物与场景门槛；按历史源码版本运行。 |
| `check_completion_evidence.py` | 审计 v2.1 180 次、场景/数据包配对及未放宽的成功标准。 |
| `check_exploration_evidence.py` | 审计 v3.0 全部 126 次、材料/初态/首包配对及软体/铰接/恢复机制。 |
| `build_report.py` | 早期基础报告生成。 |
| `build_reliability_report.py` | v1.1 可靠性报告生成。 |
| `build_obstacle_report.py` | v1.2 障碍调查报告生成。 |
| `build_obstacle_reliability_report.py` | v1.3 规划改进报告生成。 |
| `build_sensing_report.py` | v1.4 合成深度感知报告生成。 |
| `build_v2_report.py` | v2.0 动态 clutter 报告生成。 |
| `build_completion_report.py` | v2.1 六页交付报告生成。 |
| `build_exploration_figures.py` | 用审计数据/真实轨迹生成区间、应变、铰接角和受损点云图。 |
| `build_exploration_report.py` | v3.0 十页拓展报告生成，含失败、统计限制和范围。 |
| `record_obstacle_demo.py` | 早期实体障碍中的物理演示录制。 |
| `record_clutter_demo.py` | 早期密集动态 clutter 演示录制。 |
| `record_completion_demo.py` | 录制并拼接 v2.1 原候选失败、同场景改进和五干扰物视频。 |
| `record_exploration_demo.py` | 录制七段拓展例子、真实 CSV/截图，并生成带介绍的拓展成片。 |
| `prepare_editing_materials.py` | 补录基础可视化，将原始录像导出为 15 段原速素材；解码检查、索引和打包。 |
| `package_submission.py` | 按指定版本和显式清单生成当期提交 ZIP；不是对整个工作目录盲目打包。 |
| `verify_submission.py` | CRC/哈希检查并独立解压提交 ZIP，校验模型/证据并运行实际物理任务。 |
| `build_file_inventory.py` | 逐文件记录 Git 暂存区内容/用途/大小/哈希；`--verify-files` 可不依赖 Git 验证下载内容。 |

旧版本工具为历史结果保留。不要在修改引擎后把旧数据的指纹改成新指纹；请重新采样。图/报告生成依赖与物理运行依赖分开安装。

### `tests/`：现有 49 项测试的文件分工

| 文件 | 验证内容 |
|---|---|
| `test_baseline.py` | 不可达/碰撞拒绝、确定性重置以及物体没有抬起时不能算成功。 |
| `test_dataset.py` | 六种实际网格、目标切换、物理释放、预检状态隔离和置信区间。 |
| `test_asset_setup.py` | 固定版本下载、失败重试及已有缓存的校验/恢复。 |
| `test_obstacle_planning.py` | 有限搜索、绕行、原路径受阻以及规划不篡改真实场景。 |
| `test_robust_obstacles.py` | 夹爪对称、已知肘部冲突与全任务预检。 |
| `test_depth_sensing.py` | 感知只用输入点/模板、空返回拒绝、状态隔离和实际抓放。 |
| `test_active_sensing.py` | 观测预算、提前停止、局部几何不足拒绝及估计驱动物理释放。 |
| `test_recovery.py` | 感知重试不重置场景、持续失联时控制器停止。 |
| `test_clutter.py` | 同时存在的动态邻物、扰动门槛、实例观测边界和实际运输。 |
| `test_local_grasps.py` | 候选前缀/数量/开口约束，以及已知手掌冲突的实际恢复。 |
| `test_completion_evidence.py` | 拒绝过期源码和被篡改的力/不安全接触“成功”标记。 |
| `test_exploration.py` | 真正 flex 变形/释放、关节可动、无模板观测隔离、实际材料/延迟、真实故障重抓和旧指纹不变。 |
| `test_exploration_evidence.py` | 拒绝把刚体伪装成软体、恢复期间重置场景和力上限违规。 |

## 文档和报告

| 文件/目录 | 作用 |
|---|---|
| `docs/DEMO_EDITING_GUIDE.md` | 演示窗口操作、15 段素材对应关系和重新导出步骤。 |
| `docs/EXPLORATION_HANDOVER.md` | 全部拓展 case、环境、结果、接口和边界。 |
| `docs/FINAL_HANDOVER.md` | v2.1 基线续作交付说明。 |
| `docs/HANDOVER_v2.0.0.md` | v2.0 接手文档、已有机制和优化建议。 |
| `docs/V2_ROADMAP.md` | 早期 v2 规划记录，不能当作最新完成状态。 |
| `docs/ASSET_ATTRIBUTION.md` | Panda、YCB、转换工具的来源、固定版本和许可证归属。 |
| `output/pdf/exploration_report_v3.0.0.pdf` | 新 126 次研究的十页英文报告。 |
| `output/pdf/final_report_v2.1.0.pdf` | 180 次局部候选配对研究的六页英文报告。 |
| `docs/report/*.pdf` | 早期报告，按文件名中的版本辨认，不与新结果混用。 |
| `docs/images/*.png` | 报告/视频讲解所需截图与数据图，具体意义见图名和报告图注。 |
| `docs/validation/v*/` | 各版本的冻结协议、summary、逐次 JSONL/CSV、配对比较；每个版本有自己的范围。 |
| `docs/validation/editing_materials/` | 15 段素材索引、候选/随机摆放和实际 GUI 开发验证。 |
| `docs/validation/submission_checks/` | 从独立解压验证中保留的实际 smoke 日志，避免上传整棵解压副本。 |

## 模型和素材子文件怎样读

| 文件类型/路径 | 作用 |
|---|---|
| `assets/panda.lock.json`、`assets/ycb.lock.json` | 来源仓库、锁定 commit 和模型文件 SHA-256。 |
| `assets/panda/panda.xml` | Panda 的关节、执行器、接触/视觉几何定义，供工作台构建器读取。 |
| `assets/panda/*.xml` | 上游示例场景/模型配置；项目会添加自己的桌面、目标和传感相机。 |
| `assets/panda/assets/*.obj`、`*.stl` | Panda 各连杆与夹爪的视觉/碰撞网格；名称对应连杆或拆分部件。 |
| `assets/ycb/ycb/*.xml` | 六种物体的模型配置，引用纹理、实际网格和碰撞拆分。 |
| `assets/ycb/ycb/<物体>/textured.obj` | 公开物体的视觉几何。 |
| `assets/ycb/ycb/<物体>/*.png` | 物体表面纹理。 |
| `assets/ycb/ycb/<物体>/*.obj`（其他） | 转换/凸分解得到的碰撞或几何部件，以对应 XML 引用为准。 |
| `assets/ycb/ycb/<物体>/textured_coacd_*.stl` | CoACD 分解出的凸碰撞部件，供 XML 引用以进行实际接触计算。 |
| 模型目录的 `LICENSE`、`README.md` | 上游许可证与模型说明，随模型保留。 |
| 模型目录的 `manifest.json` | 本地下载记录，固定版本与内容校验。 |
| `deliverables/*.mp4`、`*.zip` | 介绍成片和特定阶段的提交/素材快照，详见该目录 README。 |
| `outputs/**/trials_*.jsonl` | 每行一个完整试验结果，包含失败阶段、物理指标、种子和配置。 |
| `outputs/**/summary_*.json` | 同次运行的成功数、失败分布、样本量、区间和版本信息。 |
| `outputs/**/protocol.json` | 实验条件、配对、种子、开发/测试划分和完成状态。 |
| `outputs/**/comparison.json` | 审计根据逐次结果重算的配对比较。 |
| `outputs/**/*.csv` | 扁平试验结果或按时间记录的真实状态/力/应变/关节轨迹，列名说明单位。 |
| `outputs/**/*.mp4`、`*.png` | 实际录制源片、介绍卡/加速中间片或状态截图；以父目录 README 区分。 |
| `outputs/**/run.log` | 对应实验命令的终端输出。 |

缓存、`.venv`、本机工具/凭据、临时解压副本与原始课程附件不属于上传交付内容。原始实验/视频与 `docs/validation` 的副本不能重复计入样本。
