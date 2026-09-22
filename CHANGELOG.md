# Changelog

## v0.1.0 — 2026-09-22

- 建立 Remote Desktop Commander 到现有 Shared Terminal Bridge 的薄 Adapter。
- 增加 status、context、lease、send、job、wait、interrupt。
- JSON 作为机器可读输出。
- 完成真实 verify33 端到端验收。
- 验证 Human Ctrl+C → INTERRUPTED_BY_HUMAN → lease REVOKED。
- 验证 stale generation 写入被 STB 本地强制拒绝。
- 验证 RDC blocking wait 可由 Human Event 自动唤醒。
- 修复 terminal_submit 参数名 command → text。
