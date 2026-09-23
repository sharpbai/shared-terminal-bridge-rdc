# Shared Terminal Bridge — RDC Adapter

ChatGPT + Remote Desktop Commander 到现有 Shared Terminal Bridge（STB）的薄适配层。

## 核心原则

用户可以只说：

> 使用 STB-RDC，通过 verify33 帮我……

第一次调用使用 `stb-rdc bootstrap SESSION` 读取 session/context/policy。后续所有 Terminal 执行都必须走：

```text
ChatGPT
  ↓
Remote Desktop Commander
  ↓
stb-rdc
  ↓
Shared Terminal Bridge
  ↓
tmux
```

RDC 只是 transport。正式 Terminal 操作不得绕过 Adapter/STB，不能直接使用 RDC 的 shell/process 工具执行用户任务，也不能直接调用 tmux send-keys。

## v0.2 命令

```bash
./stb-rdc status
./stb-rdc bootstrap SESSION --lines 40
./stb-rdc context SESSION --lines 40
./stb-rdc lease SESSION
./stb-rdc send SESSION GENERATION 'command'
./stb-rdc job JOB_ID
./stb-rdc wait JOB_ID --seconds 60
./stb-rdc interrupt JOB_ID
```

## Interaction Policy

- Human-primary。
- bootstrap first，且 bootstrap 只做 discovery。
- Terminal execution path 固定为 `RDC -> stb-rdc -> STB -> tmux`。
- 禁止直接使用 RDC shell/process 执行共享 Terminal 任务。
- 禁止绕过 STB 直接 tmux send-keys。
- AI 写入必须取得 STB execution lease。
- Human interrupt → STOP_CURRENT_TURN。
- revoked generation → DENY。
- wait timeout 不等于 job timeout / command failure。

## 长任务

不再要求 ChatGPT 为调用前等待提示额外输出消息。用户已知 Remote MCP 调用期间可能没有中间文本反馈。

长任务继续使用 STB 的 job/wait 模型：

```text
lease -> send -> job_id -> wait
```

这样保留 Human Ctrl+C、Job tracking、lease revoke 和 stale generation 安全语义。

## 已验证安全基线

- RDC → Adapter → STB → verify33。
- Human Ctrl+C → INTERRUPTED_BY_HUMAN → lease REVOKED。
- stale generation → EXECUTION_LEASE_INVALID。
- blocking wait 可由 Human Event 自动唤醒。

旧 shared-terminal-bridge 项目保持不变。
