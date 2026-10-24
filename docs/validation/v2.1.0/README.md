# v2.1.0 配对候选策略评估

日期：2026-10-25。根种子：20261025。四组共 180 个实际物理 episode，全部成功和失败均保留。

baseline/local 在同一引擎内仅改变候选策略，均为 active、普通控制、一次尝试；三种目标均衡。初始场景、估计姿态及三类种子完全配对。

| 条件 | 完整成功 | 95% Wilson 区间 | 失败 |
|---|---:|---:|---|
| baseline_clutter | 54/60（90.0%） | 79.9%-95.3% | PLANNING_FAIL: 6 |
| local_clutter | 58/60（96.7%） | 88.6%-99.1% | PLANNING_FAIL: 2 |
| baseline_dense | 26/30（86.7%） | 70.3%-94.7% | PLANNING_FAIL: 4 |
| local_dense | 29/30（96.7%） | 83.3%-99.4% | PLANNING_FAIL: 1 |

| 目标 | baseline clutter | local clutter | baseline dense | local dense |
|---|---:|---:|---:|---:|
| foam_brick | 14/20 | 18/20 | 6/10 | 9/10 |
| gelatin_box | 20/20 | 20/20 | 10/10 | 10/10 |
| pudding_box | 20/20 | 20/20 | 10/10 | 10/10 |

三干扰物恢复 trial 12、23、27、45，退化 0 次，配对精确 McNemar p=0.125。五干扰物恢复 trial 12、23、27，退化 0 次，p=0.25。样本不足以据此宣称总体统计显著改善或成功率下限已达 90%。

部分实验分组并发运行，墙钟耗时仅描述本次环境，不作受控硬件效率比较。Python 3.12.15、MuJoCo 3.15.0、NumPy 2.5.3；资产版本与锁文件一致。

成功仍同时要求 80 mm 提升、1 s 保持、95% 双指接触、55 mm 放置、实际释放与桌面支撑、0.02 m/s 稳定速度、40 N 上限、邻物最大平移 20 mm、零不安全接触及目标穿入不超过 1 mm。

冻结源码 SHA-256：`0f386f1f87282a2e9485fc9254487ca93a4f58c04f614627816926a1300005b9`。

审计：`.venv/Scripts/python.exe scripts/check_completion_evidence.py`。`protocol.json` 在运行前冻结设计；JSONL 是完整证据，CSV 仅是简化索引。`comparison.json` 由审计重新计算。

`demo/` 是开发演示，排除于 180 次分母。同场景失败/成功使用根种子 20261608，五干扰物演示使用开发根种子 45。

仍使用已知盒形透明外观代理、理想实例掩码和仿真碰撞地图，不等同于真实透明玻璃或未知堆叠杂乱场景。
