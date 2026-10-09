# v1.4.0 合成透明感知协议

| 条件 | 完整放置 | 95% Wilson区间 |
|---|---:|---:|
| clean_single | 42/60（70.0%） | 57.5%–80.1% |
| damaged_single | 0/60（0.0%） | 0.0%–6.0% |
| temporal | 41/60（68.3%） | 55.8%–78.7% |
| multiview | 59/60（98.3%） | 91.1%–99.7% |

每组60次，三种YCB代理各20次。主种子20261501；scene_seed=20262501+trial_id；sensor_seed=20361501+trial_id。
所有条件settled pose完全配对，无物理重试和失败重采样。
clean_single:无缺失，单帧；damaged_single:98%独立缺失，单帧；temporal:相同缺失64帧一视角；multiview:64帧两视角交替。
96x96理想正交射线，0.5 mm z噪声；传感器模拟场景几何，估计器只接收测量点和已知mesh。
minimum_points=24，12–120mm高度门控，361个yaw候选。
所有物理成功判据和模型属性保持原值。所有失败保留，仅summary.output_dir规范为相对路径。
模型为透明外观盒状代理，非真实玻璃折射；规划仍用真实模拟几何，不声称纯视觉。
演示seed44不计入独立正式样本；开发seed43不计入。
源SHA256：2ccaff59654439d3fcd0a09b09ce675149bb990500d1e7bddb05cdf2ed6f7e5e
