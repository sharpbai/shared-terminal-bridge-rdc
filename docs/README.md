# 文档导览

STB-RDC 是薄适配层，文档也保持小而有明确入口。

| 想了解什么 | 从哪里开始 |
| --- | --- |
| 为什么需要 STB-RDC、怎样使用 | [项目 README](../README.md) |
| 安装、命令和故障排查 | [快速上手](getting-started.md) |
| 组件职责和安全边界 | [架构说明](architecture.md) |
| 修改代码和运行测试 | [开发维护](development.md) |
| 自动测试、真实链路回归和历史证据 | [验证目录](validation/README.md) |

使用者通常只需阅读 README 和快速上手；修改某个局部时，先按根目录 `AGENTS.md` 的定位表进入对应模块，不必通读所有文档。版本化验收记录只作为证据查阅，不是当前操作手册。

## 组织规则

- 根目录 `README.md` 只承担项目背景、核心流程、快速开始和文档入口。
- `getting-started.md` 面向使用者，`development.md` 面向维护者，`architecture.md` 只解释稳定边界。
- `validation/README.md` 保存当前验证方法；`validation/vX.Y-e2e.md` 保存不可变的历史证据。
- 行为变化只更新职责对应的文档，避免在多篇文档复制同一套命令和说明。
