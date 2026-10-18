# STB-RDC 任务调用协议

当前 revision：`model-tasks-v2`。模型只传命令、请求 ID 和 job ID，不管理授权计数。旧 lease/submit/generation 契约不保留。

## 最短接入

首次发现优先直接运行只读 `stb-rdc bootstrap SESSION --lines 20`，减少一轮 PID/stdin 编排。成功后不再 help 或第二次 bootstrap；终端刷新使用 context。stdin bootstrap 同样支持，但不是必须。默认规则精简；CLI `--detailed` 或 bootstrap `params.detailed=true` 获取完整解释，不用于例行准备。所有目标命令仍只走下面的 stdin 路径。

1. RDC `start_process` 使用固定参数 `{"command":"stb-rdc serve-stdio","timeout_ms":1}`。**1 毫秒，不是 1000，不省略使用默认值。** 启动字符串不含目标命令。
2. 取得 PID 后立即 `interact_with_process`，input 为一行 JSON，末尾附换行。接收程序输出响应后退出；下一条请求另启进程，不复用 PID。结果收集可设 timeout_ms=3000。

```json
{"id":"NEW_UNIQUE_ID","op":"bootstrap","session":"local-57"}
```

bootstrap 返回有界上下文、规则、完整 startup_request 与后续模板，仅发现、不申请执行权限、不输入终端。已有当前契约和明确环境时，不例行重复读文档或 bootstrap。模型不能假设 SSH 对面的主机。

## 执行与任务句柄

```json
{"id":"NEW_UNIQUE_COMMAND_ID","op":"run","session":"local-57","params":{"text":"df -h /","expected_duration_ms":1000,"resource_class":"normal","wait_ms":600000}}
```

Core 内部授权、提交并等待，返回 job ID、状态和有界结果。新调用按接收顺序授权，包括 daemon 重启后；同 ID 重试只观察原任务，不重新执行。除 wait_ms/wait_id 可改变外，重试保持原命令参数。冲突或崩溃状态不明确时停止重放，不换 ID 猜测重试。

| op | 参数与用途 |
| --- | --- |
| bootstrap | session；可选 lines 为 1–100，默认 20 |
| run | session 或 pane、命令及逻辑 ID；Core 执行并等待 |
| wait / job | job_id；继续观察原任务 |
| input | job_id，text 或 key 二选一；Envelope id 用于输入去重 |
| interrupt | 仅 job_id；Agent Ctrl+C，不伪装 Human 事件 |
| approve | 审批 request_id；必须先取得明确人工批准，不自动执行 |
| context / state | session 或 pane，只读观察 |
| info / sessions | 发现能力或受管会话 |

Envelope 为 `id`、`op`、可选 session、可选对象 params。所有 id 都用新唯一字符串；run 或 input 的传输重试保留同 ID。session 与 params.pane 不同时指定。旧 lease/submit、原审批传参和显式授权字段直接拒绝，无兼容回退。

旧 job 的 input/interrupt 不能影响新任务。审批沿用 Core 的可信后续人工决定或本地批准校验；RDC 不伪造 Codex 身份。run 的资源批准仍用 long_run_approval_id，批准后新执行使用新逻辑 ID，命令必须匹配。

## 等待与错误

RDC 远程单次收集最多约 3 秒；较长 run/wait 在接收进程中继续等待，随后读取该 PID 输出，不能重复输入或重交命令。Core 检查点返回后，使用 job/wait 继续观察。

Human Ctrl+C 取消旧执行链，不允许自动重放；之后的新明确 run 可继续。取消等待不等于停止任务。检查点和超时不是执行失败，也不授权自动发送 Ctrl+C。高风险操作仍需批准。

一进程只处理一条换行结尾 JSON。空 EOF 无输出退出；损坏、超长（1 Mi 字符）或不完整请求输出错误后退出；第二条请求不会执行。JSON 不额外反转义，真实多行执行仍禁用，控制键不作为命令文本注入。响应过滤内部元数据，不改写终端命令或输出字符串。

## 验证与维护

Adapter 普通测试不依赖真实服务。Core 的 socket/隔离 tmux 回归覆盖 run 去重、重启自动授权、job 输入/中断隔离、审批和取消等待。默认模型契约需要新 Core，升级后重启 Bridge；Codex 需重连 MCP 刷新工具列表。

Core 接口语义见[模型任务接口](../../shared-terminal-bridge/docs/reference/model-tasks.md)。历史吞吐对照和当日记录见[验证目录](validation/README.md)。本地计时不代表网络与模型整轮延迟。
