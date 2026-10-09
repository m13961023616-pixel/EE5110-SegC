# v1.2.0 实体挡板对照证据

每目录仅含一次正式评估的 JSON 汇总、JSONL 全部 trial、CSV；全部 360 次物理结果保留。

| 目录 | 方法与环境 | 完整放置 |
|---|---|---:|
| clear_direct | 无挡板原直线，同一挑战工作区 | 55/60 |
| barrier_direct | 22 cm 挡板原直线 | 0/60 |
| barrier_rrt | 22 cm 挡板 RRT | 50/60 |
| barrier_clearance | 22 cm 挡板净空 + RRT | 54/60 |
| tall_rrt | 28 cm 挡板 RRT | 41/60 |
| tall_clearance | 28 cm 挡板净空 + RRT | 44/60 |

协议：开发 seed=43；冻结后正式 seed=20261301。物体按随机打乱的六物体块选取，每物体 10 次。
每 trial 单独 scene_seed=seed+1000+trial_id、planner_seed=seed+100000+trial_id；规划随机数不会改变后续摆放。
六组 object_id、scene_seed 和 settled spawn_pose 在审计中逐次完全对应。
同一源 SHA-256、MuJoCo/Python/NumPy 版本、固定资产 commit、环境和控制配置在汇总记录中。

挑战 x/y spawn=(原 x 范围, [-0.10,0.06]) m，放置中心=(0.48,0.30) m；全部对照一致。
该工作区不同于历史 v1.1.0，所以 clear_direct 才是本次配对对照。
原 lift/hold/contact/place/release 判据不变；物体挡板穿透超过 1 mm 会否决名义成功。
不进行物理重抓、不重采样、不删除失败。RRT 预检调用与候选过滤不算实际抓取尝试。

22 cm hybrid 相对 RRT：恢复 5、退化 1；28 cm：恢复 3、退化 0。
这不证明总体成功率至少 90%，也不说明每个物体都可靠；22 cm foam_brick 为 7/10。
28 cm hybrid 只有 44/60，未掩盖困难场景。每物体样本量仅 10，解释应结合报告置信区间。

复现：`python scripts/benchmark_obstacles.py`。审计：`python scripts/check_obstacle_evidence.py`。
JSON 中 config.output_dir 仅规范为仓库相对路径，其余元数据和逐次结果未修改。
局限：已知姿态、静态固定宽度挡板、单刚体；无 estimated perception、clutter 或 recovery。
