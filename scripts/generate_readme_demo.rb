#!/usr/bin/env ruby
# frozen_string_literal: true

require "cgi"
require "fileutils"

OUT = File.expand_path("../assets/readme-demo/frames", __dir__)
FileUtils.mkdir_p(OUT)

FRAMES = [
  {
    step: "01 发起远程任务", badge: "REMOTE REQUEST", color: "#38bdf8", active: 0,
    terminal: [["verify33 · Ubuntu · managed tmux", "#94a3b8"], ["", "#fff"],
               ["verify33 %", "#4ade80"], ["", "#fff"],
               ["# 终端保持原样，尚未执行命令", "#64748b"]],
    chat: [["USER", "#38bdf8"], ["通过 RDC 检查 verify33 的磁盘占用，", "#f8fafc"],
           ["确认后再帮我清理。", "#f8fafc"], ["", "#fff"], ["CHATGPT", "#a78bfa"],
           ["先建立 STB-RDC 上下文，只读观察。", "#cbd5e1"]],
    footer: "人在任意位置提出意图 · 操作落到实体机器的真实 tmux"
  },
  {
    step: "02 RDC Bootstrap", badge: "TRANSPORT ONLY", color: "#38bdf8", active: 2,
    terminal: [["$ stb-rdc bootstrap verify33 --lines 40", "#e2e8f0"],
               ["session   verify33", "#cbd5e1"], ["pane      %5", "#cbd5e1"],
               ["policy    STB_RDC_EXCLUSIVE", "#38bdf8"], ["lease     NONE", "#94a3b8"],
               ["status    READY", "#4ade80"]],
    chat: [["RDC", "#38bdf8"], ["已连接远程设备并启动 Adapter。", "#f8fafc"],
           ["", "#fff"], ["POLICY", "#a78bfa"], ["RDC 只负责 transport/bootstrap。", "#cbd5e1"],
           ["目标操作必须经过 STB。", "#fbbf24"]],
    footer: "不直接调用 RDC shell/process · 不绕过 STB 或 tmux ACL"
  },
  {
    step: "03 只读观察", badge: "NO LEASE", color: "#38bdf8", active: 4,
    terminal: [["verify33 % df -h /", "#e2e8f0"],
               ["Filesystem   Size  Used Avail Use% Mounted on", "#94a3b8"],
               ["/dev/vda1    120G  112G  8.0G  94% /", "#fb7185"], ["", "#fff"],
               ["verify33 % du -xhd1 /var | sort -h", "#e2e8f0"],
               ["12G  /var/log", "#fbbf24"], ["8.4G /var/cache", "#fbbf24"]],
    chat: [["STB CONTEXT", "#38bdf8"], ["根分区使用率 94%。", "#f8fafc"],
           ["主要空间来自日志和包缓存。", "#cbd5e1"], ["", "#fff"], ["下一步", "#a78bfa"],
           ["展示完整清理命令，等待批准。", "#cbd5e1"]],
    footer: "观察不申请 Execution Lease · 只返回有界终端增量"
  },
  {
    step: "04 授权并执行", badge: "LEASE GEN 7", color: "#4ade80", active: 4,
    terminal: [["即将执行：", "#94a3b8"],
               ['sudo journalctl --vacuum-time=14d && \\', "#f8fafc"],
               ["  sudo apt-get clean", "#f8fafc"], ["", "#fff"],
               ["[Human approved]", "#4ade80"],
               ['verify33 % sudo journalctl --vacuum-time=14d && \\', "#e2e8f0"],
               ["  sudo apt-get clean", "#e2e8f0"]],
    chat: [["EXECUTION LEASE", "#4ade80"], ["session    verify33", "#cbd5e1"],
           ["pane       %5", "#cbd5e1"], ["generation 7 · ACTIVE", "#4ade80"],
           ["", "#fff"], ["命令经 Adapter → STB 可见提交。", "#f8fafc"]],
    footer: "完整命令先展示给人 · 每次远程写入都校验 lease/generation"
  },
  {
    step: "05 远程等待", badge: "EVENT WAIT", color: "#fbbf24", active: 4,
    terminal: [["Vacuuming done, freed 13.2G of journals.", "#cbd5e1"],
               ["Cleaning package cache...", "#cbd5e1"],
               ["[██████████████████░░] 90%", "#fbbf24"], ["", "#fff"],
               ["Human 可在实体终端随时按 Ctrl+C", "#64748b"]],
    chat: [["STB JOB / WAIT", "#fbbf24"], ["Bridge 在目标机器本地等待。", "#f8fafc"],
           ["ChatGPT 不轮询完整 scrollback。", "#f8fafc"], ["", "#fff"],
           ["完成、取消或 Human Override", "#cbd5e1"], ["都会沿 RDC 反向唤醒会话。", "#cbd5e1"]],
    footer: "长等待留在本地 · 变化发生时才跨远程链路返回"
  },
  {
    step: "06 返回结果", badge: "COMPLETED", color: "#4ade80", active: 4,
    terminal: [["verify33 % df -h /", "#e2e8f0"],
               ["Filesystem   Size  Used Avail Use% Mounted on", "#94a3b8"],
               ["/dev/vda1    120G   81G   39G  68% /", "#4ade80"], ["", "#fff"],
               ["✓ reclaimed 31G", "#4ade80"], ["verify33 %", "#4ade80"]],
    chat: [["RESULT", "#4ade80"], ["磁盘使用率 94% → 68%", "#f8fafc"],
           ["释放空间约 31G。", "#f8fafc"], ["", "#fff"], ["AUDIT", "#38bdf8"],
           ["命令、输出、授权和事件均已记录。", "#cbd5e1"]],
    footer: "ChatGPT 获得结果与证据 · 完整历史仍保留在远程 tmux"
  },
  {
    step: "07 Human First", badge: "HUMAN OVERRIDE", color: "#fb7185", active: 4,
    terminal: [["verify33 %", "#4ade80"], ["", "#fff"],
               ["Ctrl+C → HUMAN_INTERRUPT", "#fb7185"],
               ["         lease generation 7 REVOKED", "#fb7185"], ["", "#fff"],
               ["旧远程决策：DENIED before pane", "#fbbf24"]],
    chat: [["STB-RDC", "#a78bfa"], ["任意位置发起任务", "#f8fafc"],
           ["同一个真实远程 Shell", "#f8fafc"], ["默认观察 · 明确授权", "#f8fafc"],
           ["", "#fff"], ["人的接管始终拥有最高优先级。", "#4ade80"]],
    footer: "RDC 扩展可达范围 · STB 保持本地安全语义"
  }
].freeze

def esc(value)
  CGI.escapeHTML(value.to_s)
end

def lines_svg(lines, x:, y:, size: 17, gap: 40)
  lines.each_with_index.map do |(text, color), i|
    next "" if text.empty?
    %(<text x="#{x}" y="#{y + i * gap}" fill="#{color}" font-size="#{size}" font-family="SFMono-Regular, Menlo, Monaco, 'PingFang SC', monospace">#{esc(text)}</text>)
  end.join("\n")
end

def pipeline_svg(active)
  nodes = [["ChatGPT", 90, 112], ["RDC", 258, 100], ["stb-rdc", 414, 112],
           ["STB", 582, 100], ["remote tmux", 738, 138]]
  nodes.each_with_index.map do |(label, x, width), i|
    lit = i <= active
    next_x = nodes[i + 1]&.at(1)
    out = %(<rect x="#{x}" y="69" width="#{width}" height="31" rx="15" fill="#{lit ? '#38bdf8' : '#334155'}" opacity="0.16" stroke="#{lit ? '#38bdf8' : '#334155'}"/>)
    out += %(<text x="#{x + width / 2}" y="90" text-anchor="middle" fill="#{lit ? '#bae6fd' : '#64748b'}" font-size="13" font-weight="700" font-family="Inter, 'PingFang SC', sans-serif">#{label}</text>)
    out += %(<path d="M #{x + width + 7} 85 H #{next_x - 9}" stroke="#{i < active ? '#38bdf8' : '#334155'}" stroke-width="2"/>) if next_x
    out
  end.join("\n")
end

FRAMES.each_with_index do |frame, index|
  svg = <<~SVG
    <svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675">
      <defs>
        <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#07111f"/><stop offset="1" stop-color="#111827"/></linearGradient>
        <filter id="shadow"><feDropShadow dx="0" dy="14" stdDeviation="20" flood-color="#000" flood-opacity="0.34"/></filter>
      </defs>
      <rect width="1200" height="675" fill="url(#bg)"/><circle cx="1110" cy="-20" r="260" fill="#1d4ed8" opacity="0.15"/><circle cx="40" cy="700" r="260" fill="#0e7490" opacity="0.15"/>
      <text x="42" y="40" fill="#f8fafc" font-size="24" font-weight="700" font-family="Inter, 'PingFang SC', sans-serif">Shared Terminal Bridge · RDC</text>
      <text x="430" y="40" fill="#64748b" font-size="16" font-family="Inter, 'PingFang SC', sans-serif">ChatGPT 远程清理磁盘</text>
      <rect x="942" y="17" rx="15" width="216" height="32" fill="#{frame[:color]}" opacity="0.14"/><text x="1050" y="39" text-anchor="middle" fill="#{frame[:color]}" font-size="14" font-weight="700" font-family="Inter, sans-serif">#{esc(frame[:badge])}</text>
      #{pipeline_svg(frame[:active])}
      <g filter="url(#shadow)"><rect x="42" y="122" width="704" height="472" rx="16" fill="#0b1220" stroke="#263449"/><rect x="42" y="122" width="704" height="48" rx="16" fill="#151f30"/><rect x="42" y="154" width="704" height="16" fill="#151f30"/><circle cx="68" cy="146" r="6" fill="#fb7185"/><circle cx="89" cy="146" r="6" fill="#fbbf24"/><circle cx="110" cy="146" r="6" fill="#4ade80"/><text x="394" y="152" text-anchor="middle" fill="#94a3b8" font-size="15" font-family="SFMono-Regular, Menlo, monospace">remote host · verify33 · pane %5</text>#{lines_svg(frame[:terminal], x: 66, y: 207)}<rect x="67" y="548" width="10" height="22" fill="#4ade80" opacity="#{index.even? ? '0.95' : '0.30'}"/></g>
      <g filter="url(#shadow)"><rect x="766" y="122" width="392" height="472" rx="16" fill="#101827" stroke="#303d55"/><rect x="766" y="122" width="392" height="48" rx="16" fill="#192338"/><rect x="766" y="154" width="392" height="16" fill="#192338"/><circle cx="794" cy="146" r="12" fill="#10a37f"/><text x="794" y="151" text-anchor="middle" fill="#fff" font-size="13" font-weight="700" font-family="Inter, sans-serif">G</text><text x="818" y="152" fill="#e2e8f0" font-size="16" font-weight="700" font-family="Inter, 'PingFang SC', sans-serif">ChatGPT</text><text x="1132" y="152" text-anchor="end" fill="#64748b" font-size="13" font-family="Inter, 'PingFang SC', sans-serif">#{esc(frame[:step])}</text>#{lines_svg(frame[:chat], x: 792, y: 211, size: 16)}</g>
      <rect x="42" y="620" width="1116" height="1" fill="#263449"/><text x="600" y="650" text-anchor="middle" fill="#94a3b8" font-size="16" font-family="Inter, 'PingFang SC', sans-serif">#{esc(frame[:footer])}</text>
    </svg>
  SVG
  File.write(File.join(OUT, format("frame-%02d.svg", index)), svg)
end

puts "Generated #{FRAMES.length} SVG frames in #{OUT}"
