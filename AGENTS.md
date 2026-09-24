# STB-RDC 维护指南

STB-RDC 是 ChatGPT Instant 经 RDC 调用本地 STB 的薄适配层。目标是让人和 Agent 只读取小范围文件，就能安全理解和修改。

## 先读哪里

- 命令参数或 API 映射：`stb_rdc/cli.py`
- Unix socket 与错误处理：`stb_rdc/client.py`
- Bootstrap 和交互约束：`stb_rdc/policy.py`
- 版本和默认 socket：`stb_rdc/config.py`
- 使用方式：`README.md`、`docs/getting-started.md`
- 开发方式：`docs/development.md`
- 当前验证策略：`docs/validation/README.md`
- 历史实测证据：`docs/validation/vX.Y-e2e.md`（仅在追溯行为时阅读）

## 不可破坏的边界

- 正式路径始终是 `ChatGPT → RDC → stb-rdc → STB → tmux`。
- Adapter 不直接操作 tmux，不复制 lease、job 或 Human Event 状态机。
- RDC 只负责设备发现和结构化传输，不用 shell、process、filesystem 绕过 STB。
- Bootstrap 只发现，不申请 lease，不执行用户任务。
- Wait 超时不等于 job 失败；Human Override 必须停止当前模型回合。
- 保持现有 CLI 参数和 JSON 契约兼容，除非明确做版本化变更。

## 修改原则

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
