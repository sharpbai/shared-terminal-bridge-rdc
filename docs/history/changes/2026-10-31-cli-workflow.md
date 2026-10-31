# 2026-10-31：RDC 调用路径与低负担 CLI 入口

本页是随 STB-RDC v0.4.0 / STB v0.18.0 整理的当日记录，不是全链路已验收声明。现行入口见[快速上手](../../guides/getting-started.md)、[任务调用协议](../../reference/stdio-transport.md)，早期试验见[分阶段验证记录](2026-10-31-validation-stages.md)。Core 的权限和运行加载边界见[STB 当日记录](../../../../shared-terminal-bridge/docs/history/changes/2026-10-31-cli-task-simplification.md)。

## 问题与收口

- 原始 stdin 虽减少 Shell 转义，但 RDC input 仍要 JSON 编码，而且产生启动、输入、收集多步编排。最终采用工具编码的 Base64 启动参数，不再向进程写入命令。
- bootstrap 中重复的安全策略、兼容版本、ready 和执行模板增加阅读负担。通用规则仅来自 Core instructions，Adapter 只解释自己的传输路径，成功返回完整引导，失败直接报错。
- run_text/run_base64 曾像“命令名”，实际是工作流标签。现在示例直接标注 RDC tool/arguments，并写明参数填入哪个工具。
- input 与 run 的边界容易混淆。最终移除 input 命令与模板，Agent 只提交 CLI 任务，程序提示/TUI 请人工操作；不把既有任务检查设为接入前置。

## 最终调用路径

1. 已知会话直接 bootstrap，使用已有画面确认实际环境；未知名称才 list。不重复 help/bootstrap/context。
2. 简单命令走 --text；超过 200 个 Unicode 字符或包含引号、反斜杠、反引号、美元符时，先用 ChatGPT 可用的代码执行工具按 UTF-8 编码并解码回验，再走 --base64。无编码工具时报告，不手算、不通过 RDC 先传原文编码。
3. 两种模式均使用 RDC start_process，arguments 包含 command、timeout_ms=1，启动即提交，不调用 interact_with_process。PAYLOAD 必须替换为工具实际输出。
4. 先用启动已返回输出；未收齐才 read_process_output，使用实际数字 PID、offset=0、timeout_ms=3000。同一请求持续读取，不重提 run；后续 job/wait/interrupt 使用新进程。
5. wait 模板带 --seconds 60，可设 1–600 秒；这是 Core 观察窗口，不是 RDC 的毫秒 timeout，不是命令执行期限。
6. 所有调用保持同一实际设备；多设备在线时 arguments 增加实际 deviceId。RDC PID 与 STB job_id 不能混用；流程标签不是工具或命令，JSON 示例外壳也不是 command 内容。

## 输出与代码组织

bootstrap 提供 session、terminal_state、context、instructions、transport、commands、workflow；有活动任务才附最小 current_jobs，--detailed 只增加版本与错误来源。不返回 protocol_revision、ready、missing_capabilities 或另一套通用策略。context 不带旧租约 execution，但不清除任务，也不删除权威任务中断结果。

命令参数看 stb_rdc/cli.py，编码看 command_input.py，汇总和输入选择看 policy.py，完整 RDC 参数路径看 workflow.py。tool 示例按已连接工具文档核对，使用当前实际命名空间；参数结构和 CLI 可解析性有自动回归。

## 验证与部署口径

v0.4.0 / STB v0.18.0 发版前按最终源码重跑：Adapter 40 项、Core 196 项默认测试（13 项跳过）、跨仓库 socket 2 项、宿主机隔离 tmux 16 项通过；编译及 diff 检查通过。

最终移除 input 后 Adapter 40 项默认测试通过；此前同日 tool/arguments 阶段为 41 项，数量变化来自移除旧输入测试，不是测试失败。Core 最终默认 196 项（13 项跳过），Base64 阶段另有 2 项跨仓库 socket 和 16 项隔离 tmux 通过。

未重新完成真实 ChatGPT/RDC 插件业务全链路验收；不能把本机单元测试或耗时视为整轮模型体验。Adapter 新进程直接读取源码，但 Core 最后一轮 instructions 更新和 MCP 工具移除仍需重启/重连加载。本轮整理纳入 v0.4.0 发版，Git 标签和 GitHub Release 是发布事实来源；未同步 Notion。
