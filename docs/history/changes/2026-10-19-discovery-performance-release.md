# 2026-10-19：精简发现、调用性能与 v0.3.0 发布

按北京时间记录当天调整、两轮实操对比及发布证据。前序 JSONL 演进见 [10 月 18 日记录](2026-10-18-jsonl-transport.md)；当前操作契约只维护在 [JSONL 调用说明](../../reference/stdio-transport.md)。

## 从问题到最终设计

| 问题 | 当日落地 |
| --- | --- |
| 复杂命令被启动 Shell 展开 | 固定启动 serve-stdio，通过 stdin JSONL 承载真实命令；不二次反转义 |
| 常驻接收使 RDC 等满收集窗口 | 一请求、一响应、flush 后退出，不等 EOF，不复用 PID，无常驻 worker |
| 模型机械管理授权 | run 映射一次 Core terminal_run；输入和中断用 job ID，移除旧 lease/send/submit/generation 契约 |
| 首次 help 后重复 bootstrap | 默认帮助附 Agent bootstrap 入口；发现成功后不重复，刷新终端用 context |
| bootstrap 内容过重 | 默认精简规则，完整解释通过 --detailed 或 params.detailed=true 按需获取；保留安全约束和任务模板 |
| 为发现本身也拆启动与输入 | 首次优先一次只读 CLI bootstrap；真正目标命令仍只走 stdin |

默认输出最终选择为：**保留完整命令帮助，只额外提示 Agent 调用 bootstrap；具体规则和请求模板仍在 bootstrap。** 不把帮助页扩展成第二份协议说明，也不要求已知入口的模型先调用空命令/help。

同一 Fake Bridge 测试上下文下，紧凑序列化结果为精简版约 2.98 KB、完整说明版约 5.39 KB，减少约 45%。这不是固定线上体积；实际终端历史、session/state 和序列化格式会影响大小。日志超过 4 KiB 的省略标记只是历史存储限制，不证明当时模型没收到完整响应。

## 实操对比：统计 DNS 解析情况

证据来自同一 ChatGPT 会话“统计dnsmasq解析性能2”的会话摘要与 RDC 本机工具历史。未保存原始会话正文或目标查询内容。以下两次请求相近但查询范围不完全相同，不是严格同负载 benchmark。

| 指标 | 00:20 轮 | 00:30 轮 |
| --- | --- | --- |
| 工具调用 | 7 次 | 5 次 |
| 准备 | help、bootstrap 两次 | 读 README、bootstrap、收取发现输出 |
| 实际 run | 2 次 | 1 次，收齐更多统计 |
| 首次至最后工具记录跨度 | 约 39 秒 | 约 25 秒 |
| RDC 本机处理时长之和 | 1,707 ms | 379 ms |
| Core job elapsed_ms | 73 + 34 ms | 81 ms |

工具记录跨度缩短约 36%，调用次数减少约 29%。job elapsed 已含在 RDC 调用处理耗时内，不能重复相加；也不能把本机处理以外的时间全部算成模型推理，那里还包含远程网络与平台调度。

### 00:20 轮时间线

| 北京时间 | 动作 | 本机耗时 |
| --- | --- | --- |
| 00:20:34 | help | 404 ms |
| 00:20:38 | bootstrap，4 行 | 363 ms |
| 00:20:45 | 再 bootstrap，1 行 | 346 ms |
| 00:20:50 | 启动接收进程 | 46 ms |
| 00:20:57 | 第一次 run | 307 ms |
| 00:21:06 | 启动接收进程 | 36 ms |
| 00:21:13 | 第二次 run | 205 ms |

两次 bootstrap 不由协议要求；只改变 lines，不能缩短固定规则。可见记录不能确定模型内部为何重调。会话元数据完成时间早于后两次工具记录，时间口径不一致，因此不据其计算精确的用户到最终回答耗时。

### 00:30 轮时间线

| 北京时间 | 动作 | 本机耗时 |
| --- | --- | --- |
| 00:30:08 | 读 README 前 160 行，约 6.97 KB | 43 ms |
| 00:30:15 | CLI bootstrap，timeout_ms=1 | 41 ms |
| 00:30:20 | 收取 bootstrap 输出 | 1 ms |
| 00:30:25 | serve-stdio 启动，timeout_ms=1 | 38 ms |
| 00:30:33 | stdin run 并返回完成 | 256 ms |

收益来自：不再 help 或重复 bootstrap，并把查询合并成一次 run。两轮都没有新的租约报错或等待卡住；本轮目标 job 约 81 ms，瓶颈已经不在命令执行。

## 已实施与待优化分界

已实施：无参数帮助的 Agent 引导、一次只读 bootstrap、精简默认规则、run 合并机械步骤、一次性 stdin 生命周期、serve-stdio 明确 1 ms 启动。执行权限、去重、人工中断及风险审批没有因压缩说明而放宽。

仍可优化但**尚未据此改动代码**：

1. 已有契约时不例行读 README；有环境变化才重新发现，不能为省轮次盲用陈旧主机上下文。
2. CLI bootstrap 是会自行退出的只读调用，可给短输出收集窗口，避免 1 ms 后再单独读取。serve-stdio 则仍必须 1 ms 尽快返回 PID，不能把两种启动混为一谈；短窗口数值尚未固定验收。
3. 在同一风险边界内一次收齐相关只读指标；不能为了合并而执行需先分析前一步才能决定的操作。

冷启动目标为一次 bootstrap 加一次 run 的启动/输入，共约 3 次工具调用；已有当前契约时执行约 2 次。只是目标，不承诺每次达到；输出未收齐、长任务或错误仍需额外观察。

## 发布与验证

本页后续随同日文档整理从 validation 移至 history/changes；当前协议、架构和使用入口分别进入 reference/guides，验证目录只维护回归与证据。该文档整理晚于发布，不修改已发布标签和运行语义。

- Adapter v0.3.0，提交 `cd4eb1e`，[GitHub Release](https://github.com/sharpbai/shared-terminal-bridge-rdc/releases/tag/v0.3.0)。
- 配套 Core v0.16.0；详见 [Core 当日发布记录](../../../../shared-terminal-bridge/docs/history/changes/2026-10-19-model-api-release.md)。
- 43 项 Adapter 测试、编译和差异检查通过；两仓库 GitHub CI 均通过。
- 测试覆盖精简/完整 bootstrap、CLI 与 stdin 一致性、无参数帮助不连接 Bridge、特殊字符、单帧退出、去重与任务接口。
- 实操证明真实 ChatGPT → RDC → Adapter → Core 的新版只读业务查询可完成；不能外推为所有长 wait、人工中断和故障恢复的插件端到端场景都已重新验收。
- 版本发布不重启 Bridge；Adapter 按请求新启进程，无常驻 worker。真正多行执行仍未实现。
