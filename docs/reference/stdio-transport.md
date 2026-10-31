# STB-RDC 任务调用协议

## 输入方式

首次 `stb-rdc bootstrap SESSION` 已包含环境画面、Core instructions、命令和 RDC workflow，无需重复发现。默认 context 40 行，run/wait/interrupt 观察 60 秒；观察结束不代表目标命令停止。

等待模板：`stb-rdc wait JOB_ID --seconds 60`。`--seconds` 可设 1–600 秒，默认 60，状态变化时可能提前返回；这是 Core 观察窗口，不是 RDC 的 timeout_ms，超时不会停止目标任务。

`run` 二选一：`--text TEXT` 或 `--base64 PAYLOAD`。
input 命令已移除；Agent 仅运行非交互 CLI 任务，优先 CLI 参数，不自动操作 TUI 或回复运行程序。
已删除 stdio/stdin 输入参数，不保留兼容模式。

命令不超过 200 个 Unicode 字符，且不含单引号、双引号、反斜杠、反引号或美元符时优先 --text；其他情况用 --base64。编码前先核对可执行单行内容，不猜测修复终端复制的折行。

Base64 由 ChatGPT 当前可用的代码执行工具生成：UTF-8 → 标准 Base64，无折行、不添加首尾换行，随后解码与原始字节比较。禁止模型手算、改写编码结果；无工具时明确报告。不通过 RDC 先传原文编码，以免把转义问题前移。该工具仅处理文本，不执行目标命令，不改变风险确认要求。

CLI 严格检查标准 Base64 和 UTF-8，然后按原文校验：非空、单行、无 ASCII 控制字符，最多 65536 UTF-8 字节。多行或尾随换行报错，不自动截断、去空格或拆分。Base64 不是加密，体积约增三分之一；不承诺启动参数或目标终端支持任意长度输入。

## RDC 完整调用路径

workflow 示例统一采用 `{"tool": "start_process", "arguments": {"command": "stb-rdc wait JOB_ID --seconds 60", "timeout_ms": 1}}`。`tool` 指 RDC 实际工具，`arguments` 才是传入该工具的参数，不将整个示例传为 command。run_text/run_base64 是说明标签，不是 CLI 命令。

收集示例为 `{"tool": "read_process_output", "arguments": {"pid": 12345, "offset": 0, "timeout_ms": 3000}}`；12345 只是数字格式示例，必须替换为实际返回 PID。offset=0 读取新输出。多设备在线时，在启动与收集的 arguments 中都添加相同实际 deviceId；设备不明确先 list_devices，仅一台可省略。示例使用工具短名，调用时选择当前 RDC 对应工具，不写死平台命名空间。

1. 未知会话名先 list，已知名称直接 bootstrap；利用已有画面确认实际环境后执行 run，不例行检查旧任务。
2. 简单命令直接启动；复杂命令先工具编码并回验，再启动。两种模式都启动即提交，不使用 interact_with_process 或 stdin。
3. 所有 start_process 显式 timeout_ms=1。优先使用已返回输出，结果未收齐时 read_process_output(pid=原 PID, offset=0, timeout_ms=3000) 继续读取；进程退出也需读完剩余输出。RDC 的 running/waiting/timeout 不是任务状态，以完整结果 JSON 为准。
4. COMPLETED 且结果完整时继续；RUNNING 或观察超时另启 wait JOB_ID；NEEDS_ATTENTION 按返回原因决策；INTERRUPTED_BY_HUMAN 遵守 Core instructions 停止旧链。
5. 遇到交互提示或 TUI 报告并请人工操作，不通过新 run 伪装回复。需要中断另启 interrupt JOB_ID，未确认结束继续观察，不重复中断。
6. 只有实际遇到任务占用时按返回 job_id 查询，必要时 info 找回；不强行覆盖，不把它变成接入前置步骤。

```text
start_process(command="stb-rdc run SESSION --text 'df -h /'", timeout_ms=1)
或
start_process(command="stb-rdc run SESSION --base64 PAYLOAD", timeout_ms=1)
→ 输出未收齐：read_process_output(pid=返回的 PID, offset=0, timeout_ms=3000)
```

PAYLOAD 替换为编码工具真实输出。每次 CLI 处理一次请求、输出结果后退出；后续操作使用新进程，不复用旧 PID 提交请求。PID 是 RDC 进程，job_id 是 STB 任务，不能混用。尚未返回 job_id 时继续收集原 PID，不重提 run。结果不明确或调用报错按真实证据处理，不自动重试。

## Bootstrap 输出

- session、terminal_state、context：身份、状态及画面；context 不带旧租约 execution 历史。
- instructions：运行 Core 返回的通用规则，缺失直接报 BOOTSTRAP_INSTRUCTIONS_MISSING。
- transport：输入选择与 RDC 专属路径约束。
- commands：命令用途和模板；workflow：完整 RDC 调用顺序，实现在 `stb_rdc/workflow.py`。
- current_jobs：仅有活动任务时附最小摘要，不代表必须先执行查询步骤。
- diagnostics：仅 --detailed 返回版本与错误来源，不进行能力兼容协商。

## 参数、权限和任务身份

run 控制参数：--wait-ms 默认 60000，--expected-duration-ms 默认 10000，--resource-class 为 normal/high_io/full_scan；资源类别不触发审批。调用方不生成 request_id，Core 返回 job_id；不按命令文字永久去重，不因收集超时重提。

授权、请求去重、任务互斥及人工中断均由 Core 处理。执行期间人工 Ctrl+C 停止旧执行链，之后的新明确调用按接收顺序处理；高风险操作仍通过对话确认。旧 job 不得控制新任务。

不提供输入回复或任意按键入口。Agent 中断使用 interrupt，不把字面字符串反斜杠 u0003 当控制键。

## 验证

普通测试不依赖真实 RDC、daemon 或 tmux；覆盖文本/Base64 一致性、Unicode、引号/反斜杠、边界、非法编码、旧参数拒绝、一次提交与错误不重试。相邻 Core 的 socket 集成验证逐字传递；真实 tmux 测试在容器外执行。参见[模型任务接口](../../../shared-terminal-bridge/docs/reference/model-tasks.md)。
