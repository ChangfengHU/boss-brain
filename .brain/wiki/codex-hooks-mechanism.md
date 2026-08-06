# codex 生命周期 hooks 机制(0.146 实测)

## 问题是什么
codex 如何做到 Claude Code 式的 SessionStart 注入与 Stop 拦截?第三方插件怎么接入?

## 结论
- 配置在 `~/.codex/config.toml`:`[[hooks.SessionStart]]` → `[[hooks.SessionStart.hooks]]`
  `type="command"`,`command="<绝对路径>"`;`Stop` 同形。事件全集:PreToolUse/PostToolUse/
  PermissionRequest/Pre|PostCompact/SessionStart/SessionEnd/UserPromptSubmit/Subagent*/Stop。
- I/O 协议**刻意兼容 Claude Code**:stdin JSON(`cwd`/`stop_hook_active` 等),
  Stop 输出 `{"decision":"block","reason":...}` 原样可用。
- **差异**:SessionStart 输出必须是严格 JSON
  `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}`,
  纯文本 stdout 会 `SessionStart Failed`(Claude 接受纯文本,codex 不接受)。
- **信任机制**:每个 hook 按"源:事件:组:序号"生成 key,信任=规范化 TOML 的哈希
  (`command_hook_hash`→`version_for_toml`)存于 `state.trusted_hash`。未信任→静默跳过。
  授信路径:TUI 首启的 startup hooks review 提示(用户确认一次,codex 自己写哈希);
  headless 测试用 `--dangerously-bypass-hook-trust`。**不要自己伪造哈希**——复刻内部
  序列化既脆又绕过官方安全模型。
- Stop 拦截后 codex 把 reason 喂回模型继续回合,第二次 Stop 带 `stop_hook_active=true`
  (防循环语义与 Claude 相同)。

## 证据与推理
本机 e2e:`hook: SessionStart Completed`(注入后模型能复述 registry 项目);
临时仓库无证据 commit → `Stop Blocked` → 模型补真实证据 → `Stop Completed`。
schema 来源:openai/codex 仓库 `codex-rs/hooks/schema/generated/*.json`。

## 关联
[[design-philosophy]] · 命令调用名:codex 自定义 prompts 是 `/prompts:<name>` 命名空间。

## 日期与可能过期点
2026-08-05 实测于 codex-cli 0.146.0。hooks 属较新 API,codex 大版本升级后需重跑 doctor 验证。
