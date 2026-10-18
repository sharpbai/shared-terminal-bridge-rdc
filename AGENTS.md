# STB-RDC 维护指南

STB-RDC 是 ChatGPT Instant 经 RDC 调用本地 STB 的薄适配层。目标是让人和 Agent 只读取小范围文件，就能安全理解和修改。

## 先读哪里

运行任务首次接入优先一次只读 `stb-rdc bootstrap SESSION`；也支持 stdin bootstrap。返回已有 context/policy/templates 时不重复发现或例行读取完整文档，终端刷新用 context。目标命令仍只走 stdin。开发修改仍按下列代码地图定位。

- 命令参数或 API 映射：`stb_rdc/cli.py`
- RDC JSONL 数据通道：`stb_rdc/stdio.py`（命令内容不可拼入启动 Shell）
- stdin 接收进程一次请求后退出；RDC `start_process(timeout_ms=1)` 后立即输入，不复用 PID、不引入常驻 worker。
- Unix socket 与错误处理：`stb_rdc/client.py`
- Bootstrap 和交互约束：`stb_rdc/policy.py`
- 版本和默认 socket：`stb_rdc/config.py`
- 使用方式：`README.md`、`docs/guides/getting-started.md`
- 开发方式：`docs/development/maintenance.md`
- 当前验证策略：`docs/validation/README.md`
- 历史实测证据：`docs/validation/vX.Y-e2e.md`（仅在追溯行为时阅读）

## 不可破坏的边界

- 正式路径始终是 `ChatGPT → RDC → stb-rdc → STB → tmux`。
- Adapter 不直接操作 tmux，不复制 lease、job 或 Human Event 状态机。
- RDC 只负责设备发现和结构化传输，不用 shell、process、filesystem 绕过 STB。
- Bootstrap 只发现，不申请 lease，不执行用户任务。
- daemon 支持时普通执行优先 `run`；Adapter 只映射一个 Core 请求，不本地串联授权/提交/等待。启动 timeout_ms 必须显式为 1 毫秒；输入结果收集 timeout 与其分开。
- Wait 超时不等于 job 失败；Human Override 停止当次执行链，不强制结束模型回合。
- 执行期间人工 Ctrl+C 停止旧链；之后新明确调用按 Bridge 本地接收顺序内部续授权。模型不读取或传 generation；旧调用内部后续步骤不得重放，高风险仍批准，不用 RDC 绕过决策。
- 模型接口只用 run、job ID 和审批请求 ID；旧 lease/send/generation 契约已移除，不保留兼容回退。

## 修改原则

- 文档按 guides/reference/development/validation/history 分层；按日记录放 history/changes，当前协议只维护 reference。移动页面同时更新 README、代码导航和手册目录。

- 追求局部易懂和合理维护成本，不追求最短代码或设计模式数量。
- 新行为放入职责对应的小模块；不要让入口脚本重新膨胀。
- 安全语义留在 STB Core，Adapter 只做参数映射和远程友好的响应整形。
- 修改代码时同步更新相邻测试和必要文档；不要为小改动读取整个仓库或历史验收全文。
- 普通自动化测试不得依赖真实 RDC、STB daemon 或 tmux。

## 提交前

运行：

```bash
python3 -m compileall -q stb_rdc tests
python3 -m unittest discover -s tests -v
./stb-rdc --help
```

涉及真实执行语义时，再按 `docs/validation/README.md` 做一次专用 session 手工回归。通过 GitHub 插件提交后，以 CI 结果作为合并前检查。
