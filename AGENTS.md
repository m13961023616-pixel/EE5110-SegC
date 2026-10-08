# 项目协作要求

使用中文沟通。开发语言 Python 3.12，项目运行环境为 `.venv`。

用户希望开发和 GitHub 维护同步进行：完成一个明确阶段后检查 diff、运行相关验证、
更新 README/PROGRESS/CHANGELOG，并提交和推送到已经配置的项目远程。
如果用户当次要求只读、不修改或不推送，按当次要求执行。
较大功能使用分支和 PR，小范围文档更新可以直接提交到 main。
遵循 CONTRIBUTING.md，不覆盖用户改动，不重写远程历史，不编造历史提交和测试结果。

先跑通基础系统，再逐层增加复杂度；避免巨型函数或无必要重构。
IK、路径规划、控制和任务结果验证职责分开，所有 pose 采用明确的 T_A_B convention。
抓取必须由实际仿真接触完成，不使用瞬移、粘附或 weld 代替物理执行。

公开数据集随机选物体是正式课程 baseline 要求；primitive cube 是开发检查点。
保留 failure_stage 和实验配置，报告结果时明确实验适用范围。

不提交 `.venv`、`.idea`、凭据、原始课程附件和下载的机器人网格。
模型版本固定在 assets/panda.lock.json；实验日志只精选必要证据纳入 docs/validation。

F 盘 Git 操作可能需要 `-c safe.directory=F:/NUS/Semester I/EE5110/Segment C/CA`。
使用具体项目路径例外，不设置全局 `safe.directory=*`。
