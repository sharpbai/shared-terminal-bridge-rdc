# STB-RDC 维护指南

STB-RDC 是 ChatGPT Instant 经 RDC 调用本地 STB 的薄适配层。目标是让人和 Agent 只读取小范围文件，就能安全理解和修改。

## 先读哪里

首次接入用 stb-rdc bootstrap SESSION，已有画面和引导时不重复发现；开发时按下方代码地图定位。

简单命令用 `stb-rdc run SESSION --text 'df -h /'`；复杂命令用工具按 bootstrap 生成 Base64 分段与摘要后调用 `stb-rdc run SESSION --base64-chunks CHUNK1 ... DIGEST16`。不手算、不添加首尾换行，仅单行。启动即提交，不使用 stdin。RDC 启动 timeout_ms=1，结果未收齐读取原 PID，不重提。

选择标准：命令不超过 200 个 Unicode 字符且不含引号、反斜杠、反引号或美元符时优先 --text；否则 --base64-chunks。用 bootstrap 脚本生成短段与摘要，不添加首尾换行，不手算。

- 命令参数或 API 映射：`stb_rdc/cli.py`
- UTF-8 Base64 解码与单行边界：`stb_rdc/command_input.py`。
- Unix socket 与错误处理：`stb_rdc/client.py`
- Bootstrap 只读汇总 Core instructions、RDC transport/workflow 与用途+模板合并的 commands；--detailed 只加诊断，不维护第二套安全规则。成功即返回完整引导，不协商协议版本或能力标志；说明缺失或 API 调用失败直接报错。run 不额外查询 bridge_info，不自动重试。当前 pane 有执行任务才附带最小 current_jobs，不输出完整任务历史。
- 完整操作路径与 RDC --text/--base64-chunks 启动和结果收集：`stb_rdc/workflow.py`；启动即提交，不通过 interact_with_process 输入。
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
- 执行期间人工 Ctrl+C 停止旧链；之后新明确调用按 Bridge 本地接收顺序内部续授权。模型不读取或传 generation；旧调用内部后续步骤不得重放，高风险由模型通过对话确认，不用 RDC 绕过决策。
- 模型接口只用 run、job ID ；旧 lease/send/generation 契约已移除，不保留兼容回退。

## 修改原则

- JSON 中面向 Agent 的说明文案统一中文；字段名、协议标签、状态码、命令模板及终端原文不翻译，避免破坏调用和结果判断。

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
