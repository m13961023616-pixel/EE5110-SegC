# 最终运行与交付说明（v2.1.0）

本次接手以仓库的 v2.0.0 为已验证历史基线。课程原始 PDF 保留在上一级目录，不纳入代码仓库或交付包。

## 先运行

在项目根目录打开 PowerShell。本机已建立 `.venv` 并安装锁定模型和依赖，可以直接运行：

```powershell
.\.venv\Scripts\python.exe clutter_main.py --scene clutter --trials 3
.\.venv\Scripts\python.exe clutter_main.py --scene dense --trials 3
# 无界面运行与严格物理成功检查
.\.venv\Scripts\python.exe clutter_main.py --headless --scene dense --object foam_brick --seed 45 --trials 1 --require-all-success
```

也可以执行 `powershell -ExecutionPolicy Bypass -File .\RUN_PROJECT.ps1 -Scene clutter -Trials 3`。
普通入口退出码 0 只表示运行结束；任务是否成功要查看 summary，或使用 `--require-all-success`。

## 新电脑安装

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/setup_assets.py
.\.venv\Scripts\python.exe scripts/setup_ycb.py
```

核心环境是 Python 3.12、MuJoCo 3.15.0、NumPy 2.5.3。本次运行使用 Python 3.12.15；历史交接使用 3.12.10，结果分别保存，不混同版本。
本机的便携 Python 位于上一级 `.tools/python`，仅用于当前机器；正式 ZIP 不包含解释器、`.venv` 或安装包。
ZIP 已含模型与许可证，setup 会核验完整缓存，不必再次下载。全新完全断网电脑仍需先准备 Python 和依赖 wheels。

## 本次继续完成的工作

- 将历史 `IK_FAIL` 拆成每个 seed 的静态碰撞和不收敛诊断，记录碰撞对象、穿入深度和候选拒绝阶段。
- 保留旧候选顺序，增加最多 16 个由估计网格生成的倾斜/偏移候选。仍保留 80 mm 最大开口和 6 mm 间隙，不更改物理或成功门槛。
- 新参数 `--grasps baseline` / `--grasps local` 支持同一引擎内的候选策略消融，默认 local。
- 绿色放置标记由 Config 生成，中心和半径与实际判定一致。
- 新实验协议、审计、报告生成、介绍字幕视频、SHA-256 交付清单与独立解压验证工具。

开发案例使用历史根种子 20261608：旧方法 approach 中手掌碰汤罐，新候选在同场景完成物理放置。
五干扰物的同一失败案例仍可能被安全拒绝；视频中的五干扰物成功案例使用开发种子 45。
演示不计入正式成功率分母。有限恢复能力是继承实现；新实验不把候选改善称为重试收益。

## 复核与重跑

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/check_completion_evidence.py
# 旧证据只对旧源码审计
.\.venv\Scripts\python.exe scripts/check_v2_evidence.py --source-ref v2.0.0
# 新目录完整重跑 180 次：三干扰物各 60 次，五干扰物各 30 次
.\.venv\Scripts\python.exe scripts/benchmark_completion.py --output outputs/new_frozen_run --workers 1
```

新实验默认根种子 20261025，各目标均衡，baseline/local 完全配对，均采用 active、普通控制和一次尝试。
正式记录位于 `docs/validation/v2.1.0`，保留全部成功和失败、源码指纹、初始场景和物理门槛。
`--workers` 可以加速分组运行，但并发墙钟时间只能作该环境的描述，不能当作受控效率比较。
`--resume` 只复用完整分组；部分完成的分组不覆盖，换新实验目录保留原始记录。

## 报告、视频与 ZIP

- 报告：`output/pdf/final_report_v2.1.0.pdf`。
- 介绍字幕与实际仿真视频：`deliverables/demo_v2.1.0.mp4`。
- 汇总提交包：`deliverables/EE5110SegC_submission_v2.1.0.zip`。
- ZIP 内 `SUBMISSION_MANIFEST.json` 对所有交付文件记录 SHA-256。

需要重新生成展示材料时：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-video.txt -r requirements-report.txt
.\.venv\Scripts\python.exe scripts/record_completion_demo.py
.\.venv\Scripts\python.exe scripts/build_completion_report.py
.\.venv\Scripts\python.exe scripts/package_submission.py --version 2.1.0
.\.venv\Scripts\python.exe scripts/verify_submission.py --extract-to outputs/new_submission_check
```

报告是英文；介绍字幕也为英文，视频无配音。未虚构小组成员身份或个人贡献。提交前按实际小组情况补充姓名、学号和贡献声明（如课程另有要求）。

## 结论边界

仍为已知盒形透明外观代理、理想实例掩码、合成深度缺失和仿真碰撞地图；未实现真实玻璃折射、未知形状识别、堆叠杂乱抓取或实机迁移。
物理成功需同时满足提升、稳定夹持、释放、支撑、位置、速度、邻物位移、接触和力上限。
精确数字以 `comparison.json` 与最终报告为准；不将开发案例或历史实验作为新的独立泛化结果。
