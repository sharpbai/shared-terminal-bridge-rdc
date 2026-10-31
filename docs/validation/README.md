# 验证与回归

本页维护当前回归方法，不混入旧版调用步骤。已发布结果与实操性能见 [按日演进](../history/README.md)，早期链路证据见 [v0.1 验收](v0.1-e2e.md)，其中 lease/send 不是当前接口。

## 选择测试层

| 层级 | 何时运行 | 外部依赖 |
| --- | --- | --- |
| 编译、单元及 CLI smoke | 每次修改 | 无 |
| Core socket 跨仓库回归 | 文本/Base64 输入、CLI 映射、响应丢失不重放 | 相邻 Core 仓库、本地 Unix socket |
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

所有会话名和 job ID 使用当次真实值，普通 run 不生成请求 ID。以下 run 会输入终端，必须在已授权的专用测试会话执行。

1. 调用 `stb-rdc bootstrap SESSION`，确认目标身份、画面、instructions、commands 和 workflow；不应要求 ready 等已移除字段。
2. 按[任务契约](../reference/stdio-transport.md)，分别用直接文本和工具编码的 Base64 验证（每次均为新的有意执行）：

```sh
stb-rdc run TEST_SESSION --text 'printf STB_RDC_REGRESSION_OK'
stb-rdc run TEST_SESSION --base64 PAYLOAD
```

PAYLOAD 为编码工具对同一条命令按 UTF-8 编码并解码回验的实际结果；不折行、不添加换行、不手算。两种模式均通过 RDC start_process(timeout_ms=1) 启动即提交，按原 PID 读取结果，不使用 interact_with_process。测试会话须隔离，非生产 pane。

3. 检查可见命令、输出、job ID 和完成状态。模型无需提供 ID；完成输出足够时不补读。显式同 ID 的底层去重由 Core 自动测试覆盖。
4. 新 run 运行 `ping 127.0.0.1`，真人在对应 tmux client 按 Ctrl+C，确认旧 job 为 INTERRUPTED_BY_HUMAN，不能继续其旧执行链。
5. 新明确低风险 run 可按 Core 接收顺序继续；旧 job 的 interrupt 不能控制新任务。
6. 空闲 Ctrl+C 不误撤权；Agent interrupt 不伪装成人工输入。wait 超时或取消观察不得停止目标任务。
7. 长任务验证 RDC 收集窗口结束后的 PID 输出读取；不重复输入、不重新 run 猜测重发。高风险对话确认另测，不自动代替人工决定。

每条请求新进程，一响应后退出，不复用 PID。出现能力缺失、事件断流或不确定执行状态时 fail closed，不旁路测试。

## 验证证据与口径

v0.4.0 / Core v0.18.0 发版前重跑最终源码：Adapter 40 项、Core 196 项默认测试（13 项跳过）、跨仓库 socket 2 项、宿主机隔离 tmux 16 项全部通过。此条是最终发版回归，以下保留此前阶段口径。

最终移除 input 后，Adapter 40 项、Core 196 项默认测试（13 项跳过）通过。此前 Base64 阶段另有 2 项跨仓库 socket 和 16 项隔离 tmux 回归通过；不将后续模板/说明变更写成重新完成整套真实执行验收。RDC tool/arguments 模板已按已连接工具文档核对，并由结构与 CLI 可解析测试覆盖；这不等同于真实 ChatGPT/RDC 业务全链路验收。

最终变更和加载状态见[2026-10-31 整理](../history/changes/2026-10-31-cli-workflow.md)。分阶段原始结论已移至[2026-10-31 历史验证记录](../history/changes/2026-10-31-validation-stages.md)。历史计数、接口和部署状态仅对应当时阶段，运行事实以实时查询为准。发布时记录版本、测试范围、跳过项和真实加载情况，不把本机工具耗时等同于模型整轮延迟。
