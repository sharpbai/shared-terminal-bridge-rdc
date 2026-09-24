# 开发与维护

## 设计尺度

STB-RDC 由 ChatGPT 的轻量级 Instant 会话经 RDC 调用，并配合 GitHub 插件提交。Adapter 应保持薄、清楚、可局部修改：不追求最短代码，也不复制 STB Core 的状态机。

## 代码地图

| 文件 | 职责 |
| --- | --- |
| `stb-rdc` | 兼容入口和软链接路径解析 |
| `stb_rdc/config.py` | 唯一版本号、默认 socket |
| `stb_rdc/client.py` | Unix socket JSON 协议、Bridge 错误、session 解析 |
| `stb_rdc/policy.py` | Interaction Policy、上下文裁剪、discovery bootstrap |
| `stb_rdc/cli.py` | 参数解析与 STB API 的直接映射 |
| `tests/` | 无真实 RDC/STB/tmux 依赖的契约测试 |

如果修改命令参数，只读 `cli.py` 和相应测试；修改 socket 错误，只读 `client.py`；修改模型指导，只读 `policy.py`。跨模块语义变化才需要同时阅读架构文档。

## 本地检查

```bash
python3 -m compileall -q stb_rdc tests
python3 -m unittest discover -s tests -v
./stb-rdc --help
./stb-rdc bootstrap --help
```

这些检查不要求 daemon、tmux 或 RDC。真实执行语义发生变化时，再执行[验证策略](validation/README.md)中的手工回归。

README 演示素材调整后另行运行：

```bash
ruby -c scripts/generate_readme_demo.rb
ruby scripts/generate_readme_demo.rb
```

生成过程使用 `assets/readme-demo/frames/` 作为忽略的中间目录，最终只提交 GIF。

## 提交方式

通过 GitHub 插件提交时，保持每次变更聚焦于一个职责，并确认 CI 通过。CI 在 Python 3.11/3.12 上运行编译、单元测试和 CLI smoke test；真实 RDC 链路需要已授权插件和在线实体机器，因此保留为显式手工验收。

## 不应引入

- 独立 lease、job、Human Event 状态机
- 直接 tmux 操作或 RDC shell/filesystem 旁路
- 通用 RDC SDK 或复杂依赖注入框架
- 仅为了抽象而增加的一层 facade/service registry

需要这些能力时，优先修改 STB Core 或明确扩展稳定的 Bridge API。
