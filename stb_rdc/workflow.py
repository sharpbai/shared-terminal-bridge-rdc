"""STB task path expressed as concrete RDC process interactions."""
import shlex


def start_call(command: str) -> dict:
    """Only real start_process argument names belong inside arguments."""
    return {"tool": "start_process", "arguments": {"command": command, "timeout_ms": 1}}


def rdc_workflow(name: str) -> dict:
    session = shlex.quote(name)
    return {
        "usage": "run_text/run_base64 等是流程标签，不是命令。调用 RDC 对应的真实工具，把 arguments 填入参数；不要把 tool/arguments 整个对象当 command，不执行流程标签。示例正文替换为实际文本，PAYLOAD 为工具编码结果，JOB_ID 为 STB 返回值。pid 示例 12345 必须替换为 RDC 返回的实际数字，不传字符串。",
        "device": "使用同一已确认的 RDC 设备；设备不明确时先 list_devices。多台在线时每次 arguments 增加实际 deviceId，启动和收集保持一致；仅一台时可省略。工具使用当前实际命名空间，不固定前缀。",
        "observe": {
            "list_when_unknown": start_call("stb-rdc list"),
            "first": "未知会话名先 list，已知名称直接 bootstrap SESSION。本次 bootstrap 已包含终端画面，确认实际环境后执行，不重复 help/bootstrap/context。",
            "refresh": {"when": "人工操作、换机或画面不明时刷新；结果完整时不额外读取", **start_call(f"stb-rdc context {session}")},
        },
        "choose_input": "按 transport.input_selection 选择 --text 或 --base64-chunks；两者仅是本地命令传输方式，最终都执行一次 Core run。只提交非交互 CLI 任务，优先程序的非交互参数；仅单行。遇到交互提示或 TUI 请人工操作，不通过新 run 发送回复或按键。",
        "run_text": {
            "call": start_call(f"stb-rdc run {session} --text 'df -h /'"),
            "then": "命令已提交，不再向 stdin 输入，不调用 interact_with_process。先使用启动返回的输出；结果未收齐按 collect 读取该 PID。外层 Shell 参数仍须正确引用。",
        },
        "run_base64": {
            "encode": "调用 ChatGPT 当前可用的代码执行工具，仅做文本编码，不执行目标命令。将核对的单行命令按下方脚本生成分段和摘要数组。不添加首尾换行。禁止手算；工具不可用时报告。",
            "python_example": (
                'import base64, hashlib, json\n'
                'text = "printf \'%s\\\\n\' \'A read-only example for demonstrating short Base64 segments\'"  # 替换为已核对的单行命令\n'
                'data = text.encode("utf-8")\n'
                'parts = [base64.b64encode(data[i:i+72]).decode("ascii")\n'
                '         for i in range(0, len(data), 72)]\n'
                'print(json.dumps(parts + [hashlib.sha256(data).hexdigest()[:16]]))\n'
            ),
            "call": start_call(f"stb-rdc run {session} --base64-chunks CHUNK1 CHUNK2 ... DIGEST16"),
            "then": "把 Python 输出数组的原始元素按顺序用空格连接，每个元素是一个独立参数，最后一个是摘要。只调用一次 start_process，timeout_ms=1。不要传整个 JSON 数组，不改写、修补或自动重试。输出未收齐按 collect 读取原 PID。",
        },
        "collect": {
            "call": {"tool": "read_process_output", "arguments": {"pid": 12345, "offset": 0, "timeout_ms": 3000}},
            "binding": "pid=12345 只是数字格式示例，替换为本次 start_process 返回的实际 PID；offset=0 读取上次之后的新输出。远端每次收集最多等 3000 毫秒，未收齐继续同一 PID。",
            "rules": "优先使用 start_process 已返回的输出；未完成或输出未收齐才继续读取同一 PID，按顺序拼接 JSON，不重复发送输入、不重新 run。RDC 的 running/waiting/timeout 不是 STB 任务结论，以结果 JSON 为准；有剩余输出时即使进程已退出也继续读完。",
            "lifetime": "每次 stb-rdc 调用输出结果后退出；退出后不复用 PID 提交下一请求。PID 属于 RDC 进程，job_id 属于 STB 任务，不能混用。run 结果返回前可能尚无 job_id，此时只收集原 PID。",
        },
        "handle_result": {
            "completed": "COMPLETED：使用返回结果继续；结果完整时不再 context/job。",
            "running": "RUNNING 或观察窗口超时：按同一 job_id 调用 wait，必要时 job 查询；不重提 run。默认 60 秒是 STB 观察窗口，不是 RDC 启动等待或任务执行期限。",
            "attention": "NEEDS_ATTENTION 或策略检查点：根据返回原因和 instructions 决策；遇到交互提示或 TUI 时报告并请人工操作，不自动输入回复；需人工决定时报告，不盲目重试。",
            "human_interrupt": "INTERRUPTED_BY_HUMAN：按 instructions 停止旧执行链，不自动重放后续步骤。",
            "error": "调用报错直接报告真实错误；实际遇到任务占用时按返回 job_id 查询，缺少 ID 时用 info SESSION 找回，不强行覆盖。结果不明确先收集原 PID 或查询已知 job_id，不当成未执行而重提。",
        },
        "follow_up": {
            "start_rule": "每条操作都按下面的 tool/arguments 调用 RDC，使用新的 start_process；结果统一按 collect 收集，不向旧进程写入。",
            "query": start_call("stb-rdc job JOB_ID"),
            "info_when_needed": start_call(f"stb-rdc info {session}"),
            "wait": {"guidance": "--seconds 可设 1–600 秒，默认 60，可能提前返回；这是 Core 观察窗口，不是 RDC timeout_ms，超时不停止任务。",
                     **start_call("stb-rdc wait JOB_ID --seconds 60")},
            "interrupt": {"guidance": "Core 发送 Ctrl+C 并等待提示符；不输入字面转义字符串。termination_confirmed=false 时继续观察原 job，不重复中断、不提交新命令。",
                          **start_call("stb-rdc interrupt JOB_ID")},
        },
    }
