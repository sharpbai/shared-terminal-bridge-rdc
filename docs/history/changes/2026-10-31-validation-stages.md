# 分阶段验证记录（2026-10-31）

以下保留原阶段验收记录，不代表当前接口或实时部署状态。现行步骤见[验证指南](../../validation/README.md)，现行参数见[任务调用协议](../../reference/stdio-transport.md)。

说明：旧入口清理阶段的“input/approve”“保留本地人工审批”是原记录中的过时措辞；当前批准/拒绝 CLI 和 Core 审批机制已删除，风险由对话确认。曾记录的 stdio/ready 等也不适用于当前版本。生产 Bridge 后续已按人工授权重启，不能沿用各阶段“尚未重启”判断实时状态。

## 证据口径

2026-10-31 移除强制审批后：Adapter 36 项测试通过，Core 182 项默认测试通过（13 项跳过），另有 8 项宿主机 Socket/资源标签/任务保护测试及 16 项隔离 tmux 测试通过。风险确认由模型在对话中完成；批准/拒绝 CLI、审批 API、凭证及持久化审批加载均已删除，ACL、Human Override、去重和等待预算保留。尚未重启生产 Bridge，未修改运行中的任务或原始审计记录。

2026-10-31 旧入口清理后：Adapter 37 项测试通过，旧 JSONL 测试迁移为当前 CLI 发现、input/approve、错误与原始 pipe 输入测试；Core 185 项默认测试通过（13 项跳过），宿主机另跑 7 项 Socket/任务操作测试与 16 项隔离 tmux 测试，全部通过。compileall 与 diff --check 通过。移除了 CLI lease/release/watch、serve-stdio 和未发布的旧 MCP schema；保留内部授权与本地人工审批。真实 RDC 插件全链路尚未重验，生产 Bridge 尚未重启。

2026-10-31 stdin 初版验证（清理旧入口之前）：52 项默认测试通过，含真实子进程 pipe 分段输入、保持 stdin 打开仍退出、约 40KB Unicode/引号/反斜杠原文等价及双入口映射。compileall、diff --check 通过。未进行真实 ChatGPT/RDC 插件全链路验收。Core 对应 180 项默认测试（9 项跳过）与 16 项宿主机隔离 tmux 测试通过；现代 Bash 的约 12KB 命令可执行，macOS 系统旧 Bash 出现输入截断，属于独立目标终端边界，不能据此承诺所有远端支持长命令。尚未重启生产 Bridge 加载本次能力。

自动测试通过不等于真实插件全部场景已验收；本机工具耗时不是整轮模型延迟。发布时记录测试数量、跳过项、环境、CI 结果与实际加载状态；日期结论放到 `history/changes/`，专项验收结果可留在本目录。当前回归方法只维护这一份。

## v0.3.1 发布回归（2026-10-21）

46 项默认单元测试通过；compileall 和 git diff --check 通过。覆盖 interrupt 的 wait_ms 透传、CLI 等待参数、模型中断引导及精简/完整 bootstrap 的分页提示。Core 的终端执行语义由 STB v0.17.0 的 14 项宿主机隔离 tmux 回归覆盖；本次未新增真实 ChatGPT/RDC 端到端验证，不将回放测试表述为生产全链路验证。
