# STB-RDC 调整记录：JSONL 命令通道（2026-10-18）

> 历史阶段记录：常驻 worker、lease/submit 模板及“未发布”等描述反映各阶段快照，不作为当前用法。最终机制、性能对比和 v0.3.0 发布见 [2026-10-19 整理记录](2026-10-19-discovery-performance-release.md)。

本记录保存本轮本地实现、验证和边界。Adapter 版本号仍为 `0.2.5`，新增内容尚未发布新版本。日常调用以 [JSONL 使用说明](../../reference/stdio-transport.md)为准，不从历史记录复制 generation 或 job ID。

当天后续已将初版常驻接收方式改为单请求后退出；下方“本轮实现”保留初版过程，最新生命周期与补充验证见本文末尾。

## 原因：问题出在额外的 Shell 解释层

历史调用中出现过原始 awk 命令包含 `$1` / `$2`，进入 Core 后却变成 `n[]` / `s[]` 的情况。核对 RDC 调用可确认：目标命令被嵌在 `start_process` 的外层双引号中，本地 zsh 在启动 Adapter 前就展开了位置参数；内层用于目标 Shell 的单引号不能保护外层双引号中的 `$`。

因此不是“所有 RDC 调用必然损坏”，也不是“STB 天然免疫”。关键在传输路径：Codex MCP 的结构化参数不经过这层 Shell；无论调用哪个 CLI，把目标命令拼入本地 Shell 字符串都有同类风险。Adapter 内部 JSON/socket 映射的逐字测试未发现额外反转义。

## 本轮实现：前两个阶段

### 一、固定启动，标准输入传数据

新增 `stb-rdc serve-stdio`。RDC 仅用固定命令启动接收程序，保存 PID；随后用 `interact_with_process` 将 JSONL 请求送入该程序 stdin，而不是送入交互 Shell。

- Envelope 为 `id`、`op`、可选 `session` 和 `params`；命令放在 `params.text`。
- 每行请求对应一行结构化 stdout 响应；不向 stdout 混入最终汇总或日志。
- 命令中的引号、反斜杠、Unicode、`$` 等作为数据传递，不本地展开、不二次反转义。
- 损坏 JSON 返回结构化错误；超长 frame 丢弃后仍可继续处理下一帧。
- 保留原 CLI 兼容人工使用，但模型复杂命令不再推荐使用 Shell 参数形式的 `send`。

### 二、复用 Core 去重与安全约束

submit 将 Envelope `id` 映射为 Core `request_id`。重试必须保持同 ID 与全部参数；传输超时不授权换 ID 再执行。Core 缺少 `command_request_dedup` 能力时拒绝 submit，不偷偷退回旧路径。

Adapter 不复制 lease/job 状态机，不直接操作 tmux。人工 Ctrl+C 停止当次执行链；真正的新调用能否续 generation 由 Core 本地接收顺序决定，重复旧 ID 不因重试变成新授权。Bootstrap 和 interaction policy 同步表达这些约束。

代码入口：`stb_rdc/stdio.py` 管 JSONL，`stb_rdc/cli.py` 管固定启动入口，`stb_rdc/client.py` 继续负责 Unix socket，`stb_rdc/policy.py` 提供调用引导。

## 明确保留的限制

- 真正多行执行未做。JSON 能无损承载换行，不代表 Core 允许执行多行。
- 不注入脚本、marker 或临时目标文件，不假设远端装有 Python，也不改目标 Shell / TTY。
- Agent Ctrl+C 使用 `interrupt` op，不把 `\u0003` 字面量当作按键。
- Worker 顺序处理；长 wait 占用该 worker 时，用第二个固定 worker 查询或中断，不绕过 Core。
- 无损传输不修复本来就不合法的目标命令。跨崩溃无法确定是否执行时拒绝盲目重放。

## 当天验证

| 验证 | 结果 |
| --- | --- |
| Adapter 自动测试 | 24 项通过，不依赖真实 RDC、daemon 或 tmux |
| CLI worker stdout | 仅含 JSONL 响应，无多余最终输出 |
| 特殊字符语料 | awk 字段、单双引号、反斜杠、Windows 路径、正则、Unicode、字面量转义完整保留 |
| 错误输入 | 损坏帧、超长帧、缺少能力的旧 Core 拒绝均通过 |
| 跨仓库真实 Unix socket | 与 Codex 路径共用同一语料；分片输入和首次响应丢失后的同 ID 重试通过 |
| Core 隔离 tmux | 实际 Shell 输出验证通过，属于 Core 的 10 项宿主测试之一 |
| 编译和差异格式检查 | 通过 |

独立测试为 `tests/test_stdio.py`；跨仓库测试在 Core 的 `tests/test_rdc_transport_integration.py`，不是通过真实远端 RDC 插件发起的验收。

## 加载状态与下一步

当天 Core 已按人工授权重启，确认提供 `command_request_dedup=durable-submit-v1` 和 `execution_policy=local-receipt-auto-renew-v1`。Adapter 是按调用启动的程序，新启动 `serve-stdio` 会使用当前代码；本次没有另行启动远端 RDC worker 或执行真实业务命令。

下一步在专用会话验证 ChatGPT → RDC 插件 → worker 的启动、PID 生命周期、完整响应收集和长等待展示。不能将本地测试通过写成远端插件端到端已验收。代码尚未因本轮操作提交、推送或发布新版本。

Core 相关调整、123 项默认测试与重启证据见 [STB 当日记录](../../../../shared-terminal-bridge/docs/history/changes/2026-10-18-state-and-transport.md)。

## 当天后续：取消常驻接收，单请求响应后退出

对“统计dnsmasq解析性能2”的调用计时核对发现：两次业务查询在 Bridge 中约 0.11 秒、0.66 秒完成；常驻接收进程却使 RDC 每次交互等满约 3 秒。旧 CLI 进程结束后通常约 0.25–0.50 秒返回，说明主要新增开销在通用进程工具的收集窗口，而非 JSON 编解码。

按后续确认，改为 `start_process(timeout_ms=1)` 尽快取得 PID，立即 `interact_with_process` 发送一个换行结尾的 JSON。接收程序只处理一次，flush 响应后退出，不等 EOF，不复用 PID。进程正常退出只说明 Adapter 交付完成，业务结果仍以结构化响应与 job 证据为准。

本次没有合并 acquire/submit/wait，没有新增自动授权，不修改 STB Core 生产代码，不重启 Bridge。Core 侧仅调整跨仓库测试，使首次响应丢失后的重试使用新的接收实例、保留原逻辑请求 ID。

补充回归：Adapter 30 项通过；Core 命令传输与跨仓库 socket 8 项通过。新增真实子进程测试，验证 stdin 保持打开也能在一帧响应后退出；分片输入不提前执行、第二帧不执行、损坏/超长输入退出，以及 wait 必须等 Core 结果才响应。

真实 RDC 只读 info 验证也通过：启动本地计时约 44ms，输入后响应收集约 52ms，`Exit Reason: process_finished`。只查询 Bridge 信息，未申请租约或输入业务终端。该计时不含模型和远程网络往返，不能当作整轮 ChatGPT 延迟；长 wait 与业务写入仍需专用会话验收。

## 当天后续：恢复低上下文 bootstrap

对照历史版本确认，早期 bootstrap 一次返回 context/policy/workflow，模型不必通读文档。新增 stdin 时未映射 bootstrap，导致新入口退化为多次阅读 README 和协议说明。

已给 stdin 增加 `op=bootstrap`，复用原发现逻辑，返回 `protocol_revision=stdin-once-bootstrap-v1` 与 lease/submit/wait/job/interrupt 请求模板。README 顶部恢复两步启动入口；默认上下文 20 行，可选 1–100 行。模板里的 ID、generation、job ID 必须使用新唯一值或真实返回值，不能原样执行占位符。

34 项 Adapter 测试通过；真实 Bridge 的 `local-57` 只读检查通过，确认 `discovery_only=true`、`task_executed=false`，返回模板且接收进程正常退出。测试约束无 acquire、submit 或输入按键。无需重启 Core，没有合并执行步骤；旧 CLI bootstrap 保留。

## 后续：run 合并 lease/submit/wait

在 Core 新增组合接口后，stdin `op=run` 只映射一次 `terminal_run`，不在 Adapter 内拆步。Bootstrap revision 更新为 `stdin-once-run-v1`，仅在运行 daemon 提供 `terminal_run=receipt-scoped-run-v1` 时返回 run 模板，并明确优先 run，不再例行 lease/submit/wait。原独立接口保留作审批、按键和诊断用途。

启动 `timeout_ms=1` 明确为 1 毫秒而不是 1000，Bootstrap 返回完整 `startup_request` 供照用。Adapter 无法硬拦截外部 RDC 参数，不能把调用约束宣称成宿主强制能力。

本轮 Adapter 37 项通过；Core 全量 134 项和隔离 tmux 11 项通过。普通明确任务从六次 RDC 工具调用收敛为两次；首次 bootstrap 仍另需两次，长任务或异常仍可能需要继续观察。授权、人工接管、资源批准、单行和旧 ID 不重放的边界不变。

人工许可重启 Core 后，经真实 RDC bootstrap 只读核验：revision 为 `stdin-once-run-v1`，preferred_operation 为 run，Core 能力与 run 模板正常，startup_request 明确 timeout_ms=1，task_executed=false。该次本地启动计时约 40ms、输入响应约 152ms；不含网络/模型开销。未操作现有业务终端。

## 后续：任务契约 v2，不再兼容模型授权参数

旧 lease/submit 和 CLI lease/send 已移除；stdin 仅用 run 和 job ID 交互/中断，审批仅传请求 ID。默认响应隐藏内部授权与宿主回合字段，错误转换为任务级含义，终端字符串保持原样。输入请求仍去重，Core 严格拒绝旧 job 控制新任务，风险批准不放宽。

Bootstrap revision 为 `model-tasks-v2`，要求 Core `model_tasks=job-authority-v2`，不再给旧模型模板；启动保持显式 timeout_ms=1。Adapter 40 项回归通过。经人工许可重启 Bridge 后，只读 stdin bootstrap 验证模板、能力和元数据隐藏通过；未输入业务终端。全局技能和工作区指引同步任务接口。旧 MCP 进程需重连才能刷新旧工具列表。
