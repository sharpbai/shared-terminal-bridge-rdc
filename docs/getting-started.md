# 快速上手与命令参考

本文集中记录 STB-RDC 的准备、命令和故障处理。设计与信任边界见[架构说明](architecture.md)，实测结果见[验证索引](validation-index.md)。

## 运行要求

目标机器需要：

- Python 3
- Shared Terminal Bridge daemon
- 一个或多个 STB 托管 tmux session
- `/tmp/shared-terminal-bridge.sock`，或 Adapter 配置的其他 Bridge socket
- 可由 Remote Desktop Commander 调用的 `stb-rdc` 文件

Adapter 没有第三方 Python 依赖。当前仓库中的入口使用：

```bash
python3 ./stb-rdc COMMAND
```

## 准备 STB

在目标机器的 Shared Terminal Bridge 仓库中检查 daemon 和托管 session：

```bash
./stb daemon status
./stb list
```

没有 session 时可以创建：

```bash
./stb create verify33 --cwd /absolute/path
```

STB-RDC 不负责创建独立 Shell。它只发现和操作已经被 STB 标记、加入 ACL 的 managed session。

## 命令概览

```bash
python3 ./stb-rdc status
python3 ./stb-rdc bootstrap SESSION --lines 40
python3 ./stb-rdc context SESSION --lines 40
python3 ./stb-rdc lease SESSION
python3 ./stb-rdc send SESSION GENERATION 'command'
python3 ./stb-rdc job JOB_ID
python3 ./stb-rdc wait JOB_ID --seconds 60
python3 ./stb-rdc interrupt JOB_ID
```

## `status`

```bash
python3 ./stb-rdc status
```

返回 Adapter 版本、Bridge 信息、托管 session 和 Interaction Policy。它适合检查整个调用链，不会向 pane 写入内容。

## `bootstrap`

```bash
python3 ./stb-rdc bootstrap verify33 --lines 40
```

一次返回：

- Adapter 和 Bridge 版本
- session 名称、pane 和 managed metadata
- terminal state
- 最近的有界终端内容
- STB-RDC Interaction Policy
- 建议的后续工作流

`bootstrap` 是 discovery-only：不执行任务、不申请 execution lease。ChatGPT 第一次进入 STB-RDC 任务时应优先使用它，减少多次远程往返。

## `context`

```bash
python3 ./stb-rdc context verify33 --lines 40
```

返回当前 session、terminal state 和清理首尾空行后的有界内容。观察不要求 lease，也不应为了查看历史去抢占已有 lease。

## `lease`

```bash
python3 ./stb-rdc lease verify33
```

Bridge 为 session pane 创建或返回受控 execution lease。记录响应中的真实 `generation`；不要从终端文本、旧消息或审计历史推断 generation。

取得 lease 不代表可以执行任意计划。ChatGPT 仍应先展示有风险或破坏性的完整命令，并遵守 STB 的长任务批准策略。

## `send`

```bash
python3 ./stb-rdc send verify33 7 'df -h /'
```

`7` 必须替换为当前 lease generation。Adapter 将文本交给 STB `terminal_submit`，命令进入共享 pane，并返回 `job_id`。

Adapter 不创建临时脚本、marker、额外 Shell 或目标环境控制协议。复杂管道、文件传输和标准输入需求必须作为人能看见的目标命令显式提交。

## `job` 与 `wait`

```bash
python3 ./stb-rdc job JOB_ID
python3 ./stb-rdc wait JOB_ID --seconds 60
```

`job` 读取当前状态；`wait` 在 Bridge 本地等待状态变化，再通过 RDC 返回。一次 wait timeout 只结束观察窗口：

- 不表示终端命令失败。
- 不会停止 job。
- 不授权自动重试命令。
- 不授权自动发送 `Ctrl+C`。

模型可以检查最新 job 状态，并根据已有进展、原始时间预算和替代方案决定是否再次等待。

## `interrupt`

```bash
python3 ./stb-rdc interrupt JOB_ID
```

该命令由 Agent 经 STB 向 job 对应 pane 发送 `Ctrl+C`，仍需有效 generation。它不同于目标机器前真人按下 `Ctrl+C`：Agent interrupt 不应伪装成 Human Event。

## Human Override

目标机器前真人按下 `Ctrl+C` 时：

1. 按键正常到达前台进程。
2. STB Human Event Layer 识别 client 输入。
3. 当前 execution lease 被标记为 `REVOKED`。
4. blocking wait 返回 `INTERRUPTED_BY_HUMAN`。
5. 旧 generation 的写入返回 `EXECUTION_LEASE_INVALID`。
6. 当前 ChatGPT 回合停止，不自动 acquire 或继续后续步骤。

用户发送新的操作意图后，才开始新的 lease/generation 周期。

## 在 RDC 中使用

RDC 只需要远程调用 Adapter 并传递 JSON 输出。推荐顺序：

```text
bootstrap SESSION
  → 分析有界上下文
  → context（仅在确有新增信息时）
  → 展示计划/命令
  → lease
  → send
  → wait 或 job
  → 返回结果和证据
```

不要用 RDC 独立 shell/process 代替 `stb-rdc send`，也不要直接执行 `tmux send-keys`。

## 常见错误

### `STB unavailable`

检查目标机器：

```bash
./stb daemon status
./stb daemon logs
```

确认 `/tmp/shared-terminal-bridge.sock` 存在，且调用 Adapter 的用户有权访问。

### `managed session not found`

```bash
./stb list
```

确认名称完全一致，目标 session 由 STB 创建并带有 managed 标记。普通 tmux session 不应被 Adapter 自动接管。

### `EXECUTION_LEASE_INVALID`

当前 generation 已失效、被释放或被 Human Override 撤销。不要重放旧命令。当前回合若发生人工中断，应停止；收到新的用户意图后再重新申请。

### `EXECUTION_LEASE_ALREADY_ACTIVE`

如果只是查看状态，不需要 lease，使用 `context`。准备执行时，应确认当前 active lease 的所有者和任务上下文，而不是静默抢占。

### `wait` 返回但 job 仍在运行

这是正常的观察窗口超时。使用 `job` 获取当前证据；只有明显超过合理预期时，才比较替代方案并请人工决定是否中断。
