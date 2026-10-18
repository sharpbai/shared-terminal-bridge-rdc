# STB-RDC 文档入口

Agent 首次使用直接 `stb-rdc bootstrap SESSION`，按返回契约继续；无需先读这些文档。此目录供人阅读、排障和开发。

| 目的 | 页面 |
| --- | --- |
| 安装、首次接入、日常使用 | [快速上手](guides/getting-started.md) |
| 请求格式、启动/退出和重试 | [JSONL 调用契约](reference/stdio-transport.md) |
| 组件职责与安全边界 | [架构](reference/architecture.md) |
| 判断错误来自哪里 | [错误归因](reference/error-provenance.md) |
| 定位代码、测试和提交 | [开发维护](development/maintenance.md) |
| 回归步骤和验收范围 | [验证目录](validation/README.md) |
| 按日演进、性能比较、发布过程 | [历史目录](history/README.md) |

## 与 Core 的边界

Adapter 只负责发现、结构化传输和响应整形。授权、任务状态、去重及人工中断以 [Core 模型接口](../../shared-terminal-bridge/docs/reference/model-tasks.md) 为准；不在这里维护第二套状态机。

## 维护规则

`guides/` 写如何用，`reference/` 写当前契约，`development/` 写如何改，`validation/` 写如何验和验过什么，`history/changes/` 写哪天为什么变。当前内容不混入旧命令；日期记录不替代协议。历史证据保留并注明版本，跨日另开页并互链。[CHANGELOG](../CHANGELOG.md)仅列发布摘要。
