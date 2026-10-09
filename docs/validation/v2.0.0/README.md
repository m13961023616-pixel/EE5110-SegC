# v2.0.0 冻结实验

## v2.0.0：透明目标、物理 clutter 与复杂障碍

已完成主动观测、接触反馈、有限恢复和联合环境。三个或五个 YCB 干扰物同时保持重力与碰撞，障碍由挡板和两根立柱组成；透明外观目标通过实际接触夹取、搬运与释放。每次物理场景仅初始化一次，恢复不重置场景。

```powershell
.\.venv\Scripts\python.exe clutter_main.py --scene clutter --trials 3
.\.venv\Scripts\python.exe clutter_main.py --scene dense --trials 3
.\.venv\Scripts\python.exe scripts/check_v2_evidence.py
```

冻结新种子20261601，三种盒状目标均衡抽样，共270次；三组 clutter 方法逐场景精确配对。

| 条件 | 完整夹放 | 平均观测帧数 |
|---|---:|---:|
| isolated_active | 29/30（96.7%） | 24.0 |
| obstacles_active | 30/30（100.0%） | 24.0 |
| fixed_clutter | 50/60（83.3%） | 64.0 |
| active_clutter | 52/60（86.7%） | 23.7 |
| recovery_clutter | 52/60（86.7%） | 26.7 |
| dense_recovery | 25/30（83.3%） | 28.0 |

主动观测比固定预算恢复2个失败，无退化；反馈恢复在此正式实验中未增加成功数。
三干扰物中 foam_brick 为12/20，另外两种目标均20/20；五干扰物中分别为5/10、10/10、10/10。困难的foam_brick规划是主要剩余瓶颈，未达到通用90% clutter成功率。

成功还要求邻物全程最大位移≤20 mm、零不安全接触，并满足原有80 mm提升、1秒保持、95%双指接触、55 mm放置容差和40 N力上限。全部失败和每次尝试保留于`docs/validation/v2.0.0`；34项本地检查通过。

**适用范围：** 三种已知盒形的透明外观代理，理想实例掩码与标定、合成98%随机深度缺失及10%永久缺失；规划仍使用仿真碰撞几何。尚未验证真实玻璃折射、未知目标、堆叠或相互紧贴的杂乱物体。演示和报告见[v2.0.0发布页](https://github.com/m13961023616-pixel/EE5110-SegC/releases/tag/v2.0.0)。


源指纹：`c2e20bc4bacde448c68abe5ee416171fafefcc6e2b9a5d5a0aa74cc47bb8aa5d`。所有 engine 文件冻结后才启动正式评估，开发演示不计入分母。JSONL保留原始全部尝试；仅summary.output_dir改为仓库相对路径。传感器、场景、规划使用独立种子；固定和主动view schedule不同，不能称为逐像素相同观测。
