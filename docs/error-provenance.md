# 错误归因与授权边界

## 错误来源

STB-RDC 仅能分类实际到达本地 Adapter 的错误。不要推断未到达的调用执行结果。

| 层 | 示例 | 判断依据 |
| --- | --- | --- |
| ChatGPT / OpenAI | TOOL_CALL_BLOCKED | RDC 调用未发生，平台明确报告被安全检查拦截；仅由 ChatGPT 侧报告 |
| RDC | TRANSPORT_ERROR | 设备离线、MCP 远程调用失败；仅由 RDC/ChatGPT 侧报告 |
| Adapter ↔ STB | STB_TRANSPORT_ERROR / STB_EMPTY_RESPONSE / STB_INVALID_RESPONSE | 本地 Unix socket 或响应协议失败 |
| STB | EXECUTION_LEASE_INVALID、PANE_ACCESS_DENIED 等 | STB 实际返回的权威 code 与 detail |
| 目标命令 | COMMAND_FAILED | STB job 输出和退出状态提供可核实证据 |
| 目标 API | API_ERROR | 实际请求到达目标 API 并收到可核实的失败响应 |

不能因为 API 写请求遭 OpenAI 安全拦截，就称为 Clash Verge/Mihomo API 失败。没有得到目标返回时，其状态是未知，不是失败。

本地 Adapter 错误输出采用：
```json
{"ok":false,"error":{"layer":"stb","code":"EXECUTION_LEASE_INVALID","message":"...","detail":{"code":"EXECUTION_LEASE_INVALID"}}}
```
旧的纯字符串 `error` 变成结构化对象；非零退出码仍表示 Adapter 调用失败。注意上游拒绝不会产生本地 JSON。

## 操作粒度与确认

遵循 ChatGPT 对任务和风险的自然理解，不按 shell 命令次数机械要求人工批准：

- 日常只读检查和已获授权任务中的低风险连续步骤，尽量自然连贯，不额外打扰。
- 删除、覆盖、权限提升、生产服务或网络配置的重大修改等高影响操作，先向用户明确说明目标与影响，并根据风险请求确认。
- 用户已明确授权的操作，不要无理由重复索取同样的口头确认。
- STB 的 execution lease、Pane ACL、长任务批准和 Human Override 始终单独生效；它们属于本地技术执行约束，不等价于用户授权本身。
- 当上游安全层拒绝操作，立即报告拦截发生的位置和未知的下游状态，不通过改写命令、拆分隐藏步骤或旁路 STB 去规避检查。

## 变更范围

这里不引入新的审批状态机，不让 Adapter 判断命令危险性，也不改变 STB Core。模型负责对用户解释行为与请求必要授权；Adapter 仅传递明确错误；STB 强制本地 lease/ACL。
