# 原始实验与录制素材

本目录随完整分支归档。`docs/validation/` 是整理后的正式证据入口；这里保留原始运行目录、开发过程及录制源文件。相同日志可能同时存在于两处，不能把副本算成额外试验。

| 文件/目录 | 作用 |
|---|---|
| `completion_frozen_20261025/` | v2.1 的 180 次原始配对运行，含协议、逐次日志、summary 和终端输出。 |
| `exploration_frozen_20261026/` | v3.0 的 14 组、126 次原始运行，保留所有失败。 |
| `completion_demo_v21/` | v2.1 演示原片、介绍卡、开发 JSON 和截图；剪辑导出脚本的输入。 |
| `exploration_demo/` | 七个拓展的原速 MP4、2 倍速中间片、介绍卡、真实 CSV 轨迹、单次日志/截图；原速导出只用未带 `_2x` 的源文件。 |
| `editing_materials/generated/` | 新补录的基础要求素材、六种物体分别展示、候选姿态及固定/随机抓放日志。 |
| `editing_materials/gui_smoke/` | 实际 GUI 启动和抓放的开发验证记录。 |
| `completion_demo/` | 更早一次开发录制的素材，非最新成片。 |
| `exploration_dev/` | 拓展模型/算法的开发试验与诊断，不是冻结测试集。 |
| `local_dense_development/` | 密集场景候选抓取的局部开发记录。 |
| `onboarding_failure_v2/`、`onboarding_success_v2/` | 接手时复现的失败与对照结果。 |
| `diagnosis_v2.json`、`exploratory_*.json` | 规划拒绝、角度/偏移等开发诊断。 |

常见文件：`trials_*.jsonl` 是每次完整结果；`trials_*.csv` 是便于浏览的扁平表；`summary_*.json` 汇总同次运行；`protocol.json` 声明种子/条件/版本；`comparison.json` 是审计生成的比较；`run.log` 是运行输出；PNG 是截图，MP4 是录制，`*_trace.csv` 是实际状态/接触力轨迹。

录制时生成的绝对路径拼接清单、QA 临时截图、字体/模型缓存、独立解压验证副本不上传。需要重建视频时运行对应 `scripts/record_*.py` / `scripts/prepare_editing_materials.py`，它们会生成适合新电脑的路径。重新做实验请用新的输出目录，避免混淆旧记录。
