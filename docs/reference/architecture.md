# RDC Adapter 架构与信任边界

STB-RDC 是远程传输适配层，不是第二套终端系统。

```text
ChatGPT → RDC → stb-rdc → STB Core → 共享 tmux pane
                            ↑             ↑
                     授权、状态、审计    人工直接操作
```

## 各层负责什么

| 组件 | 职责 | 不负责 |
| --- | --- | --- |
| ChatGPT | 理解意图、选择目标、解释风险、根据输出决策 | 自报授权计数或伪造宿主身份 |
| RDC | 设备发现、启动 Adapter、传输 stdin/stdout | 绕过 STB 操作目标主机 |
| Adapter | session 解析、bootstrap、JSONL 映射、有界响应 | 直接操作 tmux、复制授权或任务状态机 |
| Core | Pane ACL、接收顺序、内部授权、持久去重、job/wait、人工事件、审计 | 替用户判断所有业务风险 |
| tmux | 真实 Shell、可见输入输出、历史和人工按键 | 为模型创建独立隐藏环境 |

## 发现与执行

1. 一次只读 bootstrap 返回能力、上下文、规则及模板，不取得执行权限。
2. 模型通过 stdin 提交 run，逻辑 ID 用于重试去重；Core 内部授权、输入可见命令并等待。
3. run 返回 job ID、状态和有界输出；后续 wait/job/input/interrupt 使用该 job。
4. Adapter 一请求一响应后退出；长等待仍发生在 Core，不能因 RDC 收集窗口结束而重交命令。

操作参数和生命周期只维护在 [JSONL 契约](stdio-transport.md)。

## 人工控制与失败边界

人工 Ctrl+C 仅在 STB 命令执行期间取消当前执行链。Core 按有序事件流判断任务阶段；空闲按键不撤权，Agent interrupt 不冒充人工事件。旧 job 不得控制新 job；旧 ID 重试不能重新执行。之后的新明确 run 按 Core 本地接收顺序处理授权，高风险仍须批准。

等待超时或取消观察不等于目标命令停止。提示符返回不是可信退出码，业务成功需要输出证据。损坏协议、能力缺失或状态不确定时停止猜测，不降级为旧调用或直接 Shell。

## Exclusive Mode 与隔离限制

RDC 只承担 transport/bootstrap。独立 Shell、文件、搜索等目标操作默认属于旁路，需要一次性、明确范围的人工批准，且不得绕过 Human Override、ACL 或风险批准。

目前工具说明和 Adapter 契约约束调用路径，不能声称已物理隐藏宿主所有 RDC 能力。宿主级 capability filtering 仍是后续方向，详见 [Core Exclusive Mode](../../../shared-terminal-bridge/docs/reference/stb-rdc-exclusive-mode.md)。

## 数据与上下文

Core 在本地裁剪终端输出，Adapter 返回当前判断所需上下文。不把完整 scrollback、重复规则和无变化输出反复送入模型；bootstrap 契约未变化时复用，终端新状态用 context 读取。不得因省 token 跳过主机核对或人工风险批准。
