# v0.1.0 验证证据

2026-10-09，本地 Windows / Python 3.12.10 / MuJoCo 3.15.0。

`randomized_seed42.jsonl` 为最终速度/加速度限制版本的 10 次随机 cube 原始 trial 记录。
`randomized_seed42_summary.json` 为同次运行汇总，去除与复现无关的本机输出路径。

```powershell
.\.venv\Scripts\python.exe main.py --headless --randomize --trials 10 --seed 42
.\.venv\Scripts\python.exe tests\test_baseline.py
```

结果：10/10 抓取抬升成功；4/4 回归检查通过。
用户另在 PyCharm 直接运行 main.py，并确认 GUI 效果良好。

适用范围：单个 4 cm cube，工作区及质量/摩擦参数见汇总配置。
不能用于声称一般物体或公开数据集上的成功率。

运行时间受硬件影响；新运行会生成新的带时间戳输出，不要求与存档文件逐字相同。
