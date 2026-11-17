# 更新日志

## Unreleased

暂无。

## v0.5.0 — 2026-11-17

配套 STB v0.19.0。

- 复杂命令改用 `--base64-chunks`，移除旧 `--base64` 参数。bootstrap 提供 Python 示例，每 72 字节独立编码，末尾附原始 UTF-8 字节 SHA-256 的前 16 个十六进制字符。
- 短段和摘要通过一次 RDC 启动调用传入。适配器校验摘要后才提交 Core。

## v0.4.0 — 2026-10-31

配套 STB v0.18.0。不兼容删除旧 stdio/input 及能力协商输出；Adapter 新进程直接使用新代码，Core instructions 需重启 Bridge 后加载，MCP 工具需重连刷新。真实 ChatGPT/RDC 新版业务全链路尚未重新验收。

以下为最终实现；中间 stdio/input/ready 方案不作为发布接口。调整过程见[2026-10-31 记录](docs/history/changes/2026-10-31-cli-workflow.md)。

- Agent CLI 为 list/info/bootstrap/context/run/job/wait/interrupt；删除 status、serve-stdio、input、旧授权/审批入口，不保留旧模型调用回退。
- run 仅支持 --text 或 --base64 PAYLOAD：超过 200 个 Unicode 字符或含引号、反斜杠、反引号、美元符时使用工具编码并回验的 Base64，禁止手算；严格检查 UTF-8、标准 Base64、单行和 65536 字节边界。
- RDC 一次 start_process(timeout_ms=1) 启动即提交，不使用 interact_with_process 输入。未收齐结果继续 read_process_output 原 PID，不重提；PID 与 job_id 分开，后续操作新进程。
- workflow 独立到 stb_rdc/workflow.py，所有工具调用示例使用 tool/arguments，明确参数替换、数字 PID、offset=0 和多设备 deviceId；覆盖观察、run、结果分支、job/wait/interrupt，不将旧任务查询作为接入前置。
- bootstrap 默认 40 行，Core instructions 是唯一通用规则来源；只保留 RDC 专属传输说明，命令用途与模板合并。删除 ready/协议协商/内部能力标志，失败直接报错；版本与错误来源仅在 --detailed 中附加。
- bootstrap 不携带旧 context.execution 中断历史，有活动任务才附最小摘要；context 刷新和权威任务结果保留原语义。run 不再额外查询 bridge_info 做兼容预检查，不自动重试。
- run/wait/interrupt CLI 默认观察 60 秒；wait 模板明确 --seconds 60，可设 1–600 秒，观察超时不停止目标任务，与 RDC timeout_ms 不同。
- Agent 仅提交非交互 CLI 任务；交互提示/TUI 请人工操作，不通过新 run 回复。高风险通过对话确认；Adapter 不复制 Core 授权、去重、中断或审批状态机。
- 当前指南、架构、开发地图、回归步骤按最终实现更新；分阶段验证证据归入历史。不把本机测试或参数模板检查宣称为真实 ChatGPT/RDC 业务全链路验收。

## v0.3.1 — 2026-10-21

配套 STB v0.17.0，保持 model-tasks-v2 和一次请求一次进程的调用方式，不增加模型侧授权步骤。更新后新启动的 Adapter 进程直接使用新代码；Core 修复需重启 Bridge。

- 精简及完整 bootstrap 增加 Git/systemctl 禁用分页的短提示；分页识别与自动退出完全留在 Core，不复制到 Adapter。
- 不引入 Jev／小模型或 Terminal 保活处理。

- interrupt 透传可选 wait_ms，默认在 Core 等待提示符返回；CLI 支持 --seconds（默认 600）。RDC 收集超时只读取原 PID 输出，不再次输入中断请求。

- 中断引导明确 accepted 不等于目标程序退出；新 Core 返回 termination_confirmed，未确认时继续观察原 job，不提交下一条命令。保持 Adapter 透传，不新增本地中断状态机。

- 文档改为 guides/reference/development/validation/history 五层；重写当前架构与回归入口，日期记录进入 history/changes，旧路径引用及手册目录同步更新。

## v0.3.0 — 2026-10-19

配套 STB v0.16.0，要求 Core 发布 model-tasks-v2、terminal_run 与持久去重能力。破坏性移除旧 lease/send/submit/generation 模型契约；升级 Core 后重启 Bridge，旧请求不自动重放。Adapter 为每次请求新进程，无常驻 worker 需重启。

- `stb-rdc` 无参数时显示完整命令帮助并正常退出，额外附 Agent bootstrap 入口引导；具体规则和调用模板留在 bootstrap，无需另调 help 或连接 daemon。

- 首次发现优先一次只读 CLI bootstrap，help 直接提供入口；默认返回精简安全契约，完整解释通过 `--detailed` / `params.detailed=true` 按需获取。明确 ready 后不重复 bootstrap，刷新终端改用 context；授权、执行、去重及人工中断语义不变。

- 模型任务契约 v2：移除 lease/send/submit 和显式 generation 输入，run 内部授权，input/interrupt 只绑定 job ID，approve 只传审批请求 ID。默认响应隐藏内部元数据，旧模型调用不兼容；bootstrap 返回 model-tasks-v2，新 Core 需重启。

- stdin `run` 映射 Core `terminal_run`，Bootstrap 仅在 daemon 支持时发布组合模板；普通操作不再分开 lease/submit/wait。明确启动 timeout_ms 必须为 1 毫秒，不是 1000；返回可直接使用的 startup_request，审批/去重/人工中断仍由 Core 控制。

- 恢复低上下文 bootstrap 入口：stdin 支持 `op=bootstrap`，复用既有只读发现逻辑；返回协议 revision 和后续 JSON 请求模板，README 顶部提供两步最短入口，避免例行通读说明。Core 与执行语义不变。

- `serve-stdio` 改为一次 stdin 请求、一次响应后退出，不等待 EOF，不复用进程。RDC 启动约定 `timeout_ms=1` 尽快返回 PID，随后立即输入；执行、wait、授权和去重保持不变。补充分片输入、stdin 保持打开、错误退出及跨进程重试回归。

- 增加 `serve-stdio` JSONL 通道：固定启动、stdin 结构化命令、stdout 单行结构化结果；submit 使用 Core 持久请求 ID 去重，旧 Core 缺少能力时拒绝执行。保留人工 CLI，真正多行执行仍禁用。

- 配合 Core 本地接收顺序自动续授权：Human Ctrl+C 停止当前执行链，不要求结束整个模型回合或普通人工重新授权；新调用使用返回的 generation，高风险确认保留。Bootstrap 展示 Core execution_policy，需重启 Core 后加载新语义。

## v0.2.5 — 2026-10-16

- 增加 Human Override 后的重新授权引导：明确说明 Ctrl+C 已撤销执行租约，确认终端恢复后要求针对具体会话和下一步操作重新授权。
- 不得自动重新取得租约、将含糊的“继续”直接视为重新授权，或重放被取消的未完成命令；保持 STB Core 的安全语义不变。

## v0.2.4 — 2026-10-08

- 将原先集中的单文件适配器拆分为客户端、交互策略、命令行接口和配置模块，保持命令及 JSON 接口兼容。
- 增加面向 ChatGPT Instant 和人工维护的 `AGENTS.md`、代码结构说明和文档导览。
- 增加无需真实 RDC、STB 后台服务或 tmux 的单元测试，以及 Python 3.11/3.12 持续集成检查。
- 增加版本一致性检查；真实 RDC 链路仍采用人工验收。
- 增加结构化错误归因，区分适配器、本地 Unix Socket 传输和 STB 返回的权威错误。
- 明确区分上游 OpenAI/RDC 工具调用拦截与 STB、终端命令及目标 API 失败；调用未到达适配器时，适配器无法观察该错误。
- 将人工确认的粒度与 ChatGPT 的任务意图及风险判断对齐，避免每条命令重复确认，同时继续执行 STB 的租约和人工中断机制。
- 增加错误归因单元测试及 `docs/reference/error-provenance.md` 说明文档。

## v0.2.3 — 2026-09-22

- 放弃在 Remote MCP 调用前额外输出等待提示的设计，减少额外 Token 开销及不稳定的会话编排。
- 删除长调用提示阈值、`BEFORE_REMOTE_TOOL_CALL` 等策略字段。
- 固定终端执行路径：`RDC -> stb-rdc -> STB -> tmux`。
- RDC 只负责远程传输；共享终端任务不得直接通过 RDC 的 Shell 或进程工具执行。
- 禁止直接使用 `tmux send-keys` 绕过 STB。
- 保留会话初始化发现、执行租约、任务等待、人工优先中断和旧版本租约拒绝机制。

## v0.2.2 — 2026-09-22

- 撤销 v0.2.1 中强制中断工具调用链的设计。
- `bootstrap` 继续只负责发现会话及上下文。
- 固定 `send -> job_id -> wait` 的长任务执行流程。

## v0.2.1 — 2026-09-22

- 曾尝试在 `bootstrap` 后强制向用户返回消息，再继续执行任务；因影响连续执行，后续已撤销。

## v0.2.0 — 2026-09-22

- 新增 `bootstrap SESSION` 命令。
- 终端上下文默认读取 40 行，清理开头与结尾的空行。
- 内置人工优先、执行租约、人工中断及旧版本租约拒绝等交互规则。

## v0.1.0 — 2026-09-22

- 建立 Remote Desktop Commander 与既有 Shared Terminal Bridge 之间的轻量适配层。
- 增加 `status`、`context`、`lease`、`send`、`job`、`wait`、`interrupt` 命令。
- 完成 `verify33` 真实环境的端到端验收。
- 验证真人按下 Ctrl+C 后任务状态变为 `INTERRUPTED_BY_HUMAN`、租约状态变为 `REVOKED`。
- 验证旧版本租约的后续写入会被本地 STB 强制拒绝。
