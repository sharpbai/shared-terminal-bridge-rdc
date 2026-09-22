# Shared Terminal Bridge — RDC Adapter v0.1

现有 Shared Terminal Bridge（STB）的薄 RDC 适配层。它不重写 tmux、HumanEventLayer、Execution Lease、Context Policy 或审计逻辑。

## 架构
ChatGPT → Remote Desktop Commander → stb-rdc → existing STB daemon → tmux → shared terminal

Human 继续通过 iTerm2/tmux 操作同一个 pane。AI 正式写入必须经过 STB execution lease，不直接使用 RDC 调用 tmux send-keys。

## v0.1
```bash
./stb-rdc status
./stb-rdc context SESSION --lines 80
./stb-rdc lease SESSION
./stb-rdc send SESSION GENERATION 'command'
./stb-rdc job JOB_ID
./stb-rdc wait JOB_ID --seconds 60
./stb-rdc interrupt JOB_ID
```

正常输出统一为 JSON，便于 RDC/ChatGPT 解析。

## 边界
- 只接受 STB 已托管 session。
- Adapter 不直接调用 tmux。
- Human Interrupt、lease、stale generation、安全策略全部由现有 STB 决定。
- send 必须携带 generation。
- Adapter 不隐式获取 execution lease。
- 旧 shared-terminal-bridge 项目保持不变。

## v0.1 验收
1. RDC 可调用 status。
2. 可读取托管 session context。
3. 显式 lease 后可 submit 无副作用命令。
4. wait 可作为 RDC blocking call。
5. Human Ctrl+C 后由 STB revoke lease，旧 generation 无法继续写入。
