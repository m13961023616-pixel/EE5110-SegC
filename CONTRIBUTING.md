# 开发维护约定

每次开发聚焦一个可解释、可验证的阶段。工作完成后同步维护代码、必要验证和文档。

1. 明确当前检查点和验收标准，在 `PROGRESS.md` 更新状态。
2. 新阶段使用 `feature/<主题>` 分支；修复使用 `fix/<主题>`。
3. 在 Python 3.12 独立环境中完成相关测试；有行为变化时验证物理结果。
4. 更新 `README.md` 的用法与限制，以及 `CHANGELOG.md` 的实际变化。
5. 以小而完整的提交记录阶段成果，提交说明写清改动目的。
6. 将分支推送到 GitHub；较大阶段使用 Pull Request 展示改动、测试和限制。
7. 合并后保持 `main` 是已验证的版本；按有意义的阶段建立版本标签。

提交示例：`feat: add dataset object loader`、`fix: reject colliding grasp candidates`、
`docs: record randomized grasp evaluation`。

自动验证执行失败检测/reset 检查和一次固定 cube 抓取。
批量随机物体实验在本机运行，必要时把精选结果放入 `docs/validation/`。

## 仓库内容

纳入 Python 源码、依赖版本、文档、测试、模型来源与锁定信息、精选实验证据。
`.venv/`、`.idea/`、下载的机器人网格、全部日常输出和本地工具不纳入 Git。
课程 PDF 与原始附件也不属于这个代码仓库。

模型通过 `scripts/setup_assets.py` 重新下载；`assets/panda.lock.json` 固定模型 commit 和校验和。
实际下载的许可证保留在 `assets/panda/LICENSE`；项目公开不改变第三方模型许可。

协作时保留已经工作的代码和用户本地改动；提交前检查 Git diff。
常规同步使用正常 push，不重写远程历史。

## 外接盘 Git

F 盘不记录文件所有权，Git 可能报 `detected dubious ownership`。
可以为确认可信的本项目路径使用单次命令例外：

```powershell
git -c safe.directory='F:/NUS/Semester I/EE5110/Segment C/CA' status
```

Codex 操作使用这种特定目录例外，不配置 `safe.directory=*`。
