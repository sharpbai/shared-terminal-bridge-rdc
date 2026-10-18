# 快速上手

目标设备需有 Python、已运行的 STB Core 和 PATH 可见的 stb-rdc，ChatGPT 已连接 RDC 插件。Core 应提供 `model_tasks=job-authority-v2`；旧服务先升级/重启，不兼容旧模型调用。

首次直接调用 `stb-rdc bootstrap SESSION --lines 20`，一次只读发现即可，无需先 help 或重复 bootstrap。默认返回精简规则和任务模板；`--detailed` 仅用于排障查看完整解释。运行目标命令时固定启动 `stb-rdc serve-stdio`，RDC timeout_ms 必须为 1；取得 PID 后立即输入一条 run JSON，末尾换行。程序回复后退出。

Bootstrap 一次返回上下文、调用规则和请求模板，默认流程为：

```text
首次 bootstrap → run → 解释结果
                  └→ 若未结束：按 job ID 继续观察
```

无需先申请 lease，无需读取或传递 generation。普通执行用 run，交互输入和中断使用 job ID。人工 Ctrl+C 停止旧链；新明确调用可以继续，高风险另行批准。

完整请求格式只维护在[任务协议](stdio-transport.md)，不要复制多份参数说明。

## 人工命令入口

CLI 保留 status、bootstrap、context、job、wait、interrupt 和 serve-stdio；旧 lease/send 已移除。目标命令通过 stdin JSON 的 run 输入，不放进 Shell 启动参数。

```bash
stb-rdc status
stb-rdc bootstrap SESSION --lines 20
stb-rdc context SESSION --lines 20
stb-rdc job JOB_ID
stb-rdc wait JOB_ID --seconds 60
stb-rdc interrupt JOB_ID
```

这些占位符必须替换成实际 session/job ID。interrupt 会影响该运行任务，不能当成只读探测。仅看历史或状态不取得执行权限。

## 排障

- 找不到命令：核对 PATH 或使用已确认的 Adapter 绝对路径，启动参数仍不携带目标命令。
- Core 能力缺失：重启/升级 Bridge；不要拆回旧授权步骤。
- 状态不明或响应丢失：保持逻辑 ID，不盲目换 ID 重试。
- 旧任务不可交互：观察当前终端，新任务用新 run；不把旧 job 绑定到新任务。
- 审批拒绝：等待有效人工决定，不用 RDC 旁路。

STB-RDC 用户任务只走 STB。独立 RDC 文件、进程和 Shell 操作需要另行一次性明确旁路授权。
