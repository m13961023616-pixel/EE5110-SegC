# 开发进度

日期：2026-10-09。阶段：primitive cube 的 oracle-perception 开发闭环。

## 已完成

- CA 目录可写；Python 3.12.10 独立虚拟环境。
- MuJoCo 3.15.0 / NumPy 2.5.3。
- Panda 官方模型及许可证，commit `0059d4335f8156206f63a35662313385f7ad6d74`。
- robot + table + cube 场景、固定或随机 x/y/yaw reset。
- 模块化 oracle pose → grasp → IK → 路径检查 → actuator execution。
- 物理双指夹持、抬升和 1 秒保持判定。
- JSONL trial 日志、JSON 汇总、可选场景截图。
- PyCharm 入口、配置集中管理、中文运行和代码阅读说明。

## 验证结果

- 初版固定 cube：1/1 成功。
- 加入名义关节速度/加速度限制和旋转跟踪检查后：seed=42 随机 cube 10/10 成功。
  结果在 `outputs/summary_20261009_012924_114909.json`，逐次记录在同时间戳 JSONL。
- 4/4 回归检查通过：seeded reset、不可达目标拒绝、机器人/物体相交检测、桌面物体不算 lift。

用户已在 PyCharm 运行，并确认可视化效果良好。
无界面物理运行已验证。
离屏截图已成功生成并人工视觉检查：`outputs/trials_20261009_013236_782947.png`。
对应的最终固定 cube 抓取为 1/1 成功，夹爪持有 cube，物体明显离桌。

## 尚未完成

公开 3D 数据集随机选物体是课程 baseline 的正式要求，目前尚未接入。
place、多候选 grasp、障碍物路径搜索、RGB-D、估计感知、clutter、失败恢复和扩展对照实验尚未实现。
本阶段的 10/10 仅适用于 4 cm cube、当前摩擦质量参数和指定工作区。

## 下一个开发检查点

接入公开数据集，建立多物体随机测试，再选择一个明确的挑战做技术改进。

## 版本控制

本地 Git 仓库已初始化，当前成果将作为第一个真实历史检查点。
GitHub 仓库：[m13961023616-pixel/EE5110-SegC](https://github.com/m13961023616-pixel/EE5110-SegC)，公开。
首个阶段提交 `d61d77f` 已推送，main 已跟踪 origin/main。
GitHub Actions 已在干净的 Windows / Python 3.12 环境完成依赖安装、锁定模型下载校验、
4 项回归检查和固定 cube 抓取，所有步骤通过。
[首次云端验证记录](https://github.com/m13961023616-pixel/EE5110-SegC/actions/runs/37819415123)。
阶段版本标签 `v0.1.0` 对应首次已验证 baseline 提交。
维护约定见 `CONTRIBUTING.md`，阶段记录见 `CHANGELOG.md`。
