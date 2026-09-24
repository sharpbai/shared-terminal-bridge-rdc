# Changelog

## Unreleased

- 将压缩的单文件 Adapter 拆为 client、policy、CLI 和 config 小模块，保持命令与 JSON 契约不变。
- 增加面向 ChatGPT Instant 与人工维护的 `AGENTS.md`、代码地图和文档导览。
- 增加不依赖真实 RDC、STB daemon 或 tmux 的单元测试，以及 Python 3.11/3.12 CI。
- 增加版本一致性检查，并将真实 RDC 链路明确保留为手工验收。

## v0.2.3 — 2026-09-22

- 放弃“Remote MCP 调用前额外输出等待提示”的协议设计，避免额外 token 和不稳定的 turn 编排。
- 删除长调用提示阈值、BEFORE_REMOTE_TOOL_CALL 等相关策略字段。
- 强化唯一执行路径：`RDC -> stb-rdc -> STB -> tmux`。
- 明确 RDC 仅作为 transport；共享 Terminal 任务不得直接通过 RDC shell/process 执行。
- 明确禁止直接 `tmux send-keys` 绕过 STB。
- 保留 bootstrap discovery、execution lease、job/wait、Human Override 和 stale generation 安全语义。

## v0.2.2 — 2026-09-22

- 撤销 v0.2.1 的强制中断 tool loop 设计。
- bootstrap 保持 discovery-only。
- 固化 `send -> job_id -> wait` 长任务模型。

## v0.2.1 — 2026-09-22

- 曾尝试要求 bootstrap 后强制返回用户，再继续执行；后续撤销。

## v0.2.0 — 2026-09-22

- 新增 `bootstrap SESSION`。
- context 默认 40 行并清理首尾空行。
- 内置 Human-primary、execution lease、Human Interrupt、stale generation 等协议。

## v0.1.0 — 2026-09-22

- 建立 Remote Desktop Commander 到现有 Shared Terminal Bridge 的薄 Adapter。
- 增加 status、context、lease、send、job、wait、interrupt。
- 完成 verify33 真实端到端验收。
- 验证 Human Ctrl+C → INTERRUPTED_BY_HUMAN → lease REVOKED。
- 验证 stale generation 写入被本地 STB 强制拒绝。
