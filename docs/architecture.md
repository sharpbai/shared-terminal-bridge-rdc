# 架构与信任边界

## 产品定位

STB-RDC 将 ChatGPT 的远程可达性连接到 Shared Terminal Bridge 的本地强制边界。它不是完整远程执行系统，也不复制 STB。

```text
User
  → ChatGPT
  → Remote Desktop Commander
  → stb-rdc adapter
  → Shared Terminal Bridge daemon
  → managed tmux pane
```

## 组件职责

### ChatGPT

- 理解用户意图和已有上下文。
- 选择目标设备与托管 session。
- 解释风险、展示完整命令。
- 根据结构化 job 结果决定下一步。

ChatGPT 的自觉不是最终写入安全边界。

### Remote Desktop Commander

- 发现和连接实体机器。
- 启动或调用目标机器上的 Adapter。
- 传输结构化请求和响应。

在 STB-RDC Exclusive Mode 下，RDC 不直接执行用户的目标主机任务。

### stb-rdc

- 将 session 名解析为 STB managed pane。
- 提供适合远程调用的粗粒度命令。
- 返回版本、策略、状态和有界上下文。
- 将 lease/send/job/wait/interrupt 映射到 STB API。

Adapter 不直接调用 tmux，不拥有权威 lease 状态。

### Shared Terminal Bridge

- 强制 Pane ACL。
- 管理 execution lease 和 generation。
- 关联可见命令与 job。
- 在目标机器本地等待状态变化。
- 识别 Human Event 并撤销授权。
- 保留审计记录。

### tmux

- 保存真实 Shell 与 scrollback。
- 让本地人和远程 Agent 共享同一个 pane。
- 在 client 输入层区分 Human `Ctrl+C` 与 Bridge 注入。

## 控制面与数据面

### 数据面

```text
tmux scrollback
  → STB bounded read
  → stb-rdc context/bootstrap
  → RDC response
  → ChatGPT context
```

终端内容应先在目标机器上裁剪，只传输当前判断所需的数据。

### 写入控制面

```text
new user intent
  → acquire lease/generation
  → submit visible command
  → STB validates pane + generation
  → tmux pane
```

每次写入都在目标机器本地验证，不能依赖远端调用到达顺序。

### Human 控制面

```text
physical Ctrl+C
  → tmux client key table
  → foreground process
  → STB HUMAN_INTERRUPT
  → lease REVOKED
  → wait wakes
  → RDC returns event
  → ChatGPT stops current turn
```

即使远端网络或 ChatGPT 延迟，旧 generation 也已经在目标机器本地失效。

## Bootstrap

冷启动把多个只读发现步骤合并为一次远程调用：

- Adapter/Bridge 版本
- managed session 和 pane
- terminal state
- 有界 scrollback
- Interaction Policy
- next-step guidance

它明确返回 `task_executed=false` 和 `discovery_only=true`。这样“发现成功”不会被误解为“已经获得执行权限”。

## Job 与远程等待

`send` 创建 STB job，`wait` 在目标机器本地阻塞到以下任一条件：

- 命令完成
- 出现交互提示
- Human Override
- 等待窗口到期
- 远程请求被取消

等待窗口与 job 生命周期分开。RDC 调用取消或超时，不会自动停止目标命令。

## Exclusive Mode

选择 STB-RDC 意味着选择 STB 作为目标主机 capability plane。RDC 的独立 filesystem/search/process/shell/edit 能力默认属于 bypass。

Adapter 和提示策略只能约束当前调用方式；只要宿主仍同时暴露其他 RDC 工具，模型理论上仍有绕行能力。完整硬隔离需要宿主：

1. 根据 STB-RDC task context 隐藏或拒绝目标主机的直接能力。
2. 只允许 transport/bootstrap 类操作。
3. 对一次性旁路要求 capability、operation、target 和人工批准 token。
4. 旁路结束后立即恢复 Exclusive Mode。

无论是否存在旁路，都不能覆盖 Human Override、lease revoke、Pane ACL 或 long-run approval。

## 安全不变量

- RDC 连接成功不等于执行授权。
- Bootstrap 不执行任务。
- 观察不要求 execution lease。
- 所有正式写入经过 STB。
- generation 在目标机器本地校验。
- Human `Ctrl+C` 立即撤销旧 generation。
- wait timeout 不改变 job 状态。
- Adapter 失效不应影响人继续使用 tmux。
