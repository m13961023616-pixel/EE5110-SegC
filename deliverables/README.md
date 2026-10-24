# 视频、剪辑素材和提交包

本目录现在随完整分支上传，文件可直接下载。视频均由实际 MuJoCo 运行录制；开发演示与正式统计分开。

| 文件/目录 | 作用 |
|---|---|
| `editing_materials/` | 优先用于自行剪辑：15 段独立原速视频、分析图、CSV 轨迹、开发日志和清单。 |
| `editing_materials.zip` | 与上一目录对应的整套素材压缩包，约 24.6 MB。 |
| `editing_materials/00_README.md` | 每段视频对应的内容、剪辑提示和界面启动方法。 |
| `editing_materials/CLIP_INDEX.json` | 15 段的准确时长、源录像、倍速信息和 SHA-256。 |
| `editing_materials/MANIFEST.json` | 素材包内文件的原始字节 SHA-256，不包含清单自身。 |
| `editing_materials/01_baseline/` | 5 段：工作台、六种 YCB 物体随机摆放、候选姿态、完整抓放、六次随机试验。 |
| `editing_materials/02_explorations/` | 7 段：密集遮挡、软体、铰接、未见形状、力反馈、故障恢复、稳健感知。 |
| `editing_materials/03_comparisons/` | 3 段：原候选失败、同场景改进成功、五干扰物抓放。 |
| `editing_materials/04_analysis_and_logs/` | 讲解用图、真实力/应变/关节轨迹及对应日志；用于解释机制。 |
| `explorations_v3.0.0.mp4` | 七段拓展组成的介绍字幕视频，约 3 分 33 秒；物理片段标明 2 倍速。 |
| `demo_v2.1.0.mp4` | 前一阶段介绍视频，约 2 分 20 秒，展示失败与改进及动态邻物。 |
| `EE5110SegC_submission_v3.0.0.zip` | v3.0 当时验证通过的提交快照：源码、模型/许可证、两份报告、拓展介绍视频和证据，约 26.6 MB。 |
| `EE5110SegC_submission_v2.1.0.zip` | v2.1 历史提交快照，约 23.0 MB；保留用于复现上一阶段。 |

两个 submission ZIP 保持已验证时的原始内容。后加的交互菜单、剪辑导出工具和本次文件导航以当前分支源码为准，不能把历史 ZIP 当成最新分支的完整副本。下载完整当前项目请下载本分支的 Code → Download ZIP 或克隆分支。

操作说明以 [当前演示指南](../docs/DEMO_EDITING_GUIDE.md) 为准，完整文件导航见 [根 README](../README.md)。
