# STB-RDC 演进记录

日常用法见 [快速上手](../guides/getting-started.md)，当前格式见 [JSONL 契约](../reference/stdio-transport.md)。以下是历史证据，不复制旧命令执行。

| 日期 | 记录 |
| --- | --- |
| 2026-10-19 | [精简发现、两轮性能对比与 v0.3.0 发布](changes/2026-10-19-discovery-performance-release.md) |
| 2026-10-18 | [复杂命令转义、JSONL 和单请求退出演进](changes/2026-10-18-jsonl-transport.md) |

[早期 v0.1 验收](../validation/v0.1-e2e.md)保留在验证目录，代表当时契约，不能当成现有 lease/send 用法。Core 的授权和状态机演进见 [Core 历史入口](../../../shared-terminal-bridge/docs/history/README.md)。

按日文件统一为 `changes/YYYY-MM-DD-topic.md`，记录问题、决定、验证、发布与待办；当前参数不在日期记录维护。对比指标必须说明采样范围和时间口径，不能把工具本机时长当成用户整轮延迟。
