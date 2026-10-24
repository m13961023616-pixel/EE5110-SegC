# v3.0.0：全部具体拓展方向的冻结证据

正式根种子 20261026，14 组共 126 次物理 episode。`protocol.json` 固定条件、物理门槛和开发种子；`comparison.json` 是审计从全部 JSONL 重新汇总的结果，目录内每组包含完整逐次日志和 summary。所有失败保留，没有替换场景或挑选成功种子。

| 条件 | 完整抓放成功 | 失败 |
|---|---:|---|
| crowding_single | 5/6 | trial 1：PLANNING_FAIL |
| crowding_active | 3/6 | trial 1：PLANNING_FAIL；2、3：PLACE_FAIL |
| articulated | 6/6 | 无 |
| soft_fixed | 2/6 | 3–6：SLIP_DETECTED |
| soft_adaptive | 6/6 | 无 |
| novel_prior | 11/12 | 5：SLIP_DETECTED |
| novel_points | 11/12 | 5：SLIP_DETECTED |
| force_fixed | 10/12 | 6、10：SLIP_DETECTED |
| force_adaptive | 12/12 | 无 |
| recovery_single | 0/6 | 全部 GRASP_FAIL（真实执行的受控闭合故障） |
| recovery_retry | 6/6 | 首次全部失败，第二次全部成功；不重置场景 |
| sensor_single | 6/12 | 1、2、7、8、9、11：PERCEPTION_FAIL |
| sensor_raw_fusion | 1/12 | 除 8 外均为 PLANNING_FAIL |
| sensor_robust | 9/12 | 1、5、9：SLIP_DETECTED，均为楔形 |

配对条件严格比较相同的初始广义坐标（或完整 YCB 场景）、实际材料与实例种子；受损感知还比较首个数据包 SHA-256。每次初始化一次，无机器人与目标之间的 weld，所有执行通过物理接触完成。成功要求原有 80 mm 提升、1 s 保持、至少 95% 双指接触、实际张开释放、桌面支撑、55 mm 放置误差、速度小于 20 mm/s 和 40 N 执行器上限；软体另要求边应变不超过 40%，杂乱场景另检查邻物位移和不安全接触。

主动遮挡组两次放置误差为 0.339 m 和 0.068 m，不能把感知置信度当成任务成功。软体固定/反馈组平均峰值边应变分别约 3.67% / 4.90%；反馈没有证明减小变形，失败组暴露时长也不同。新形状两种方法完全打平。稳健感知仍存在楔形滑落，受控恢复的 100% 不代表自然故障通用恢复率。

每组 6 或 12 次，仅作为机制验证和筛查。Wilson 区间、失败 trial ID、配对恢复/退化和精确 McNemar 检验均在 comparison 中；七次比较没有任何一项经 Bonferroni 校正后低于 0.05。并行运行时长不能当成受控速度比较。不同任务不合并为一个成功率。

`demo/` 下是开发根种子 43 的七个例子、实际状态/力/应变/关节 CSV 及日志，明确排除于正式 126 次；视频只在演示中使用 2 倍速播放。

```powershell
.\.venv\Scripts\python.exe scripts/check_exploration_evidence.py
```

冻结源码 SHA-256：`9f59c29b6dc0a62c15d10249788590491010c02d32f9ed1baf884d871e08c418`。

模型、观测真值边界及逐方向限制见 [交付指南](../../EXPLORATION_HANDOVER.md)。旧 v2.1 的 180 次研究独立保留，不属于这批新样本。
