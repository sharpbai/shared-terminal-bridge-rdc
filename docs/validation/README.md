# 验证策略与回归入口

本目录把“现在应该怎样验证”和“历史上实际验证过什么”分开：本文是当前维护入口；带版本号的文件是当时环境与结果的证据，不随日常代码调整重写。

## 验证分层

| 层级 | 适用范围 | 是否依赖真实环境 | 入口 |
| --- | --- | --- | --- |
| 编译与单元测试 | 每次代码修改 | 否 | `python3 -m compileall -q stb_rdc tests`、`python3 -m unittest discover -s tests -v` |
| CLI smoke test | 参数或入口修改 | 否 | `./stb-rdc --help`、`./stb-rdc bootstrap --help` |
| Bridge 只读回归 | Client、bootstrap、context 修改 | 需要本地 STB daemon | `./stb-rdc status`、`./stb-rdc bootstrap SESSION` |
| 真实写入回归 | lease、send、wait、interrupt 或安全语义修改 | 需要专用 managed tmux 和人工配合 | 本文“手工端到端回归” |

普通 CI 只运行前三项中的无外部依赖部分。RDC 授权、实体机器、STB daemon 和 tmux 属于真实环境，不应成为普通单元测试的隐式前置条件。

## 当前验证结论

STB-RDC v0.1–v0.2 已在以下真实链路验证：

```text
ChatGPT
  → Remote Desktop Commander
  → stb-rdc
  → Shared Terminal Bridge 0.14.0
  → verify33 managed tmux session
```

详细原始记录见 [v0.1 端到端验收](v0.1-e2e.md)。

## 能力矩阵

| 能力 | 结果 | 权威组件 |
| --- | --- | --- |
| Adapter/Bridge 状态发现 | 通过 | stb-rdc + STB |
| managed session 解析 | 通过 | STB session registry |
| 有界 context 读取 | 通过 | STB Observation |
| 显式 lease/generation | 通过 | STB Execution Lease |
| 可见命令提交 | 通过 | STB terminal_submit |
| job 完成识别 | 通过 | STB Job tracking |
| blocking wait | 通过 | STB local wait |
| Human Event 唤醒 wait | 通过 | STB Human Event Layer |
| Human `Ctrl+C` 权威识别 | 通过 | tmux client + STB |
| lease revoke | 通过 | STB Execution Lease |
| stale generation 拒绝 | 通过 | STB write validation |

## 实测场景

### 正常命令

```text
generation: 14
command: printf 'STB_RDC_V01_OK\n'
result: COMPLETED
evidence: output + prompt return
```

### Human Override

```text
command: ping 127.0.0.1
result: INTERRUPTED_BY_HUMAN
lease: REVOKED
stale write: EXECUTION_LEASE_INVALID
```

### Blocking wait

```text
generation: 16
command: sleep 120
Human Ctrl+C 后约 7.8 秒返回
completion_confidence: authoritative
recommended_action: STOP_CURRENT_TURN
```

## 手工端到端回归

以下步骤会写入真实托管 pane，应只对专用测试 session 执行。

### 1. 状态和 bootstrap

```bash
python3 ./stb-rdc status
python3 ./stb-rdc bootstrap verify33 --lines 20
```

确认 `bootstrap_result.discovery_only=true`、`task_executed=false`，且 Interaction Policy 要求固定执行路径。

### 2. 正常执行

```bash
python3 ./stb-rdc lease verify33
python3 ./stb-rdc send verify33 GENERATION "printf 'STB_RDC_REGRESSION_OK\\n'"
python3 ./stb-rdc wait JOB_ID --seconds 30
```

确认结果为 `COMPLETED`，pane 中能看到命令和输出。

### 3. Human Override

提交持续运行命令：

```bash
python3 ./stb-rdc send verify33 GENERATION 'ping 127.0.0.1'
python3 ./stb-rdc wait JOB_ID --seconds 60
```

在目标机器的真实 tmux client 中按 `Ctrl+C`。确认：

- wait 提前返回 `INTERRUPTED_BY_HUMAN`
- lease 为 `REVOKED`
- 使用旧 generation 的新 `send` 返回 `EXECUTION_LEASE_INVALID`
- stale command 未进入 pane

## 历史验收记录

- [v0.1 端到端验收](v0.1-e2e.md)：首次验证 RDC → Adapter → STB → tmux、blocking wait 和 Human Override。

新增历史记录时使用 `vX.Y-e2e.md`，只记录当时的日期、版本、环境、操作和证据。当前命令或通用验证方法只更新本文，避免多个版本文档同时维护同一套步骤。
