# 快速上手

何时用 Base64：命令超过 200 个 Unicode 字符，或包含单引号、双引号、反斜杠、反引号、`$` 中任一字符时，用工具编码后传 `--base64-chunks CHUNK1 ... DIGEST16`；其余短且简单的单行文本用 `--text`。字数按原文计算，不计 CLI 外层引用。run 的帮助和 bootstrap 均返回同一选择规则。

目标设备需有 Python、运行中的 STB Core 和 PATH 可见的 stb-rdc，ChatGPT 已连接 RDC。bootstrap 正常返回即发现完成；说明缺失或 API 故障直接报错，不协商旧接口版本。

简单命令用 `stb-rdc run SESSION --text 'df -h /'`；复杂命令用工具按 bootstrap 生成 Base64 分段与摘要后调用 `stb-rdc run SESSION --base64-chunks CHUNK1 ... DIGEST16`。不手算、不添加首尾换行，仅单行。启动即提交，不使用 stdin。RDC 启动 timeout_ms=1，结果未收齐读取原 PID，不重提。

Bootstrap 一次返回上下文、调用规则和命令模板，默认流程为：

```text
首次 bootstrap → run → 解释结果
                  └→ 若未结束：按 job ID 继续观察
```

无需先申请 lease，无需读取或传递 generation。普通执行用 run，观察和中断使用 job ID。人工 Ctrl+C 停止旧链；新明确调用可以继续，高风险另行批准。

完整请求格式只维护在[任务协议](../reference/stdio-transport.md)，不要复制多份参数说明。

## 人工命令入口

CLI 支持 run、list、info、bootstrap、context、job、wait、interrupt；旧 JSONL 入口已移除。普通 run 不传 ID，由 Core 生成。输入细节见[任务调用协议](../reference/stdio-transport.md)。

```bash
stb-rdc list
stb-rdc bootstrap SESSION --lines 40
stb-rdc context SESSION --lines 40
stb-rdc job JOB_ID
stb-rdc wait JOB_ID --seconds 60
stb-rdc interrupt JOB_ID
```

这些占位符必须替换成实际 session/job ID。interrupt 会影响该运行任务，不能当成只读探测。仅看历史或状态不取得执行权限。

## 排障

- 找不到命令：核对 PATH 或使用已确认的 Adapter 绝对路径；不要把复杂原文嵌入启动 Shell。
- Core 能力缺失：重启/升级 Bridge；不要拆回旧授权步骤。
- 状态不明或响应丢失：读取原 PID 或查询已返回的 job ID，不盲目重新 run。
- 旧任务不可交互：观察当前终端，新任务用新 run；不把旧 job 绑定到新任务。
- 高风险操作：先通过对话取得人工同意；不再调用审批命令。

STB-RDC 用户任务只走 STB。独立 RDC 文件、进程和 Shell 操作需要另行一次性明确旁路授权。

## 按意图选择入口

- `list`：不知道名称时列举会话；已知名称直接 `bootstrap SESSION`，只读接入，不执行任务。
- `context SESSION`：刷新同一会话的终端观察，默认 40 行；与 bootstrap 使用相同的 session、terminal_state、context 字段。
- `info SESSION`：查看所绑定主 pane 的状态及当前执行任务，恢复 job_id；不授予写入权限。
- `run`：新任务，默认观察 60 秒；`job/wait`：查询或继续观察原任务；`interrupt`：中断原任务。

Adapter 保留自己的中文帮助、调用模板及 RDC 启动/结果收集规则；会话解析、读屏、任务状态、授权、去重和人工中断均转发至 STB。Core 通用安全说明随 bridge_info 返回，并包含在 bootstrap 的 instructions 中；不向 STB 加入 RDC 协议。
