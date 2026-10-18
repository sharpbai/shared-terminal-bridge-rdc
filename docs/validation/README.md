# 验证与回归

本页维护当前回归方法，不混入旧版调用步骤。已发布结果与实操性能见 [按日演进](../history/README.md)，早期链路证据见 [v0.1 验收](v0.1-e2e.md)，其中 lease/send 不是当前接口。

## 选择测试层

| 层级 | 何时运行 | 外部依赖 |
| --- | --- | --- |
| 编译、单元及 CLI smoke | 每次修改 | 无 |
| Core socket 跨仓库回归 | JSONL、映射、重试修改 | 相邻 Core 仓库、本地 Unix socket |
| 隔离真实 tmux | 执行或中断语义修改 | Core 测试、宿主 tmux，不在容器内 |
| 插件端到端 | RDC 生命周期、业务展示或等待修改 | 已授权 RDC、在线设备、专用受管会话、真人 |

无依赖检查：

```bash
python3 -m compileall -q stb_rdc tests
python3 -m unittest discover -s tests -v
./stb-rdc
./stb-rdc --help
./stb-rdc bootstrap --help
```

socket 与 tmux 的命令只维护在 [Core 测试说明](../../../shared-terminal-bridge/docs/development/testing.md)。不要把业务终端作为自动测试前置条件。

## 专用会话端到端步骤

所有会话名、请求 ID、job ID 使用当次真实值。以下 run 会输入终端，必须在已授权的专用测试会话执行。

1. 调用 `stb-rdc bootstrap SESSION`，确认 ready、discovery_only、task_executed=false 和当前任务契约。
2. 按 [JSONL 契约](../reference/stdio-transport.md) 固定启动接收程序，stdin 发送一次 run：

```json
{"id":"NEW_UNIQUE_TEST_ID","op":"run","session":"TEST_SESSION","params":{"text":"printf STB_RDC_REGRESSION_OK","expected_duration_ms":1000,"resource_class":"normal","wait_ms":30000}}
```

3. 检查可见命令、输出、job ID 和完成状态。相同逻辑 ID 重试不能再次输入；完成输出足够时不补读。
4. 新 ID 运行 `ping 127.0.0.1`，真人在对应 tmux client 按 Ctrl+C，确认旧 job 为 INTERRUPTED_BY_HUMAN；旧 ID 重试不能恢复它。
5. 新明确低风险 run 可按 Core 接收顺序继续；旧 job 的 input/interrupt 不能控制新任务。
6. 空闲 Ctrl+C 不误撤权；Agent interrupt 不伪装成人工输入。wait 超时或取消观察不得停止目标任务。
7. 长任务验证 RDC 收集窗口结束后的 PID 输出读取；不重复输入、不换 ID 猜测重发。高风险审批另测，不自动批准。

每条请求新进程，一响应后退出，不复用 PID。出现能力缺失、事件断流或不确定执行状态时 fail closed，不旁路测试。

## 证据口径

自动测试通过不等于真实插件全部场景已验收；本机工具耗时不是整轮模型延迟。发布时记录测试数量、跳过项、环境、CI 结果与实际加载状态；日期结论放到 `history/changes/`，专项验收结果可留在本目录。当前回归方法只维护这一份。
