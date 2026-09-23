# 验证与回归索引

## 当前验证结论

STB-RDC v0.1–v0.2 已在以下真实链路验证：

```text
ChatGPT
  → Remote Desktop Commander
  → stb-rdc
  → Shared Terminal Bridge 0.14.0
  → verify33 managed tmux session
```

详细原始记录见 [v0.1 端到端验收](../VALIDATION-v0.1.md)。

## 能力矩阵

| 能力 | 结果 | 权威组件 |
| --- | --- | --- |
| Adapter/Bridge 状态发现 | 通过 | stb-rdc + STB |
| managed session 解析 | 通过 | STB session registry |
| 有界 context 读取 | 通过 | STB Observation |
| 显式 lease/generation | 通过 | STB Execution Lease |
| 可见命令提交 | 通过 | STB terminal_submit |
| job 完成识别 | 通过 | STB Job tracking |
| blocking wait | 通过 | STB local wait |
| Human Event 唤醒 wait | 通过 | STB Human Event Layer |
| Human `Ctrl+C` 权威识别 | 通过 | tmux client + STB |
| lease revoke | 通过 | STB Execution Lease |
| stale generation 拒绝 | 通过 | STB write validation |

## 实测场景

### 正常命令

```text
generation: 14
command: printf 'STB_RDC_V01_OK\n'
result: COMPLETED
evidence: output + prompt return
```

### Human Override

```text
command: ping 127.0.0.1
result: INTERRUPTED_BY_HUMAN
lease: REVOKED
stale write: EXECUTION_LEASE_INVALID
```

### Blocking wait

```text
generation: 16
command: sleep 120
Human Ctrl+C 后约 7.8 秒返回
completion_confidence: authoritative
recommended_action: STOP_CURRENT_TURN
```

## 手工回归步骤

以下步骤会写入真实托管 pane，应只对专用测试 session 执行。

### 1. 状态和 bootstrap

```bash
python3 ./stb-rdc status
python3 ./stb-rdc bootstrap verify33 --lines 20
```

确认 `bootstrap_result.discovery_only=true`、`task_executed=false`，且 Interaction Policy 要求固定执行路径。

### 2. 正常执行

```bash
python3 ./stb-rdc lease verify33
python3 ./stb-rdc send verify33 GENERATION "printf 'STB_RDC_REGRESSION_OK\\n'"
python3 ./stb-rdc wait JOB_ID --seconds 30
```

确认结果为 `COMPLETED`，pane 中能看到命令和输出。

### 3. Human Override

提交持续运行命令：

```bash
python3 ./stb-rdc send verify33 GENERATION 'ping 127.0.0.1'
python3 ./stb-rdc wait JOB_ID --seconds 60
```

在目标机器的真实 tmux client 中按 `Ctrl+C`。确认：

- wait 提前返回 `INTERRUPTED_BY_HUMAN`
- lease 为 `REVOKED`
- 使用旧 generation 的新 `send` 返回 `EXECUTION_LEASE_INVALID`
- stale command 未进入 pane

## 文档与素材检查

```bash
ruby -c scripts/generate_readme_demo.rb
ruby scripts/generate_readme_demo.rb
```

SVG 帧生成在被 Git 忽略的 `assets/readme-demo/frames/`。最终 GIF 使用 `rsvg-convert` 和 ImageMagick 合成，提交文件为：

```text
assets/readme-demo/stb-rdc-disk-cleanup-demo.gif
```
