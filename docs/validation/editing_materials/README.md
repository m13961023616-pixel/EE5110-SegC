# 剪辑素材与交互窗口的开发验证

- 15 段独立 MP4，总时长 736.35 秒（约 12 分 16 秒），800×600、20 fps、无音轨，无倍速处理。执行录像去掉 2 秒通用说明卡，保留阶段栏。全部逐帧解码通过，素材 ZIP 的 CRC 和 SHA-256 清单校验通过。
- `clip_index.json` 对应 `deliverables/editing_materials/` 中的准确时长、文件、来源与哈希。按用户后续要求，素材 ZIP/视频现在随完整分支上传。
- `visualization_metadata.json` 保存六种 YCB 随机摆放的实际姿态及局部候选生成器输出。图形显示预抓取坐标轴和接近连线；不是通过全部碰撞检查的执行路径。
- `pick_place_*`：新录制 foam_brick 固定位姿演示，1/1 完成真实抓放。
- `randomized_*`：新录制六种 YCB 的平衡随机实例，每种一次，6/6 完成。它是演示范围，不替代正式统计。
- `gui_baseline.json` 与 `gui_soft_adaptive.json`：实际打开 MuJoCo 被动窗口、运行到 SUCCESS 并自动关闭。基础通过 `OPEN_DEMO.cmd --case baseline --fast --auto-close` 启动；软体通过新 viewer 入口验证。窗口刷新限为最多 60 Hz，物理仍使用原步长。菜单输入 0 的退出也已验证。
- 旧 v2.1 180 次与新 v3.0 126 次审计再次通过；没有修改冻结引擎或把这些开发片段加入正式实验分母。

完整对应关系与操作见 [分段素材和界面指南](../../DEMO_EDITING_GUIDE.md)。
