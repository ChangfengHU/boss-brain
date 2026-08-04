/**
 * project-brains extension for pi-agent.
 *
 * Mirrors the Claude Code hooks:
 * - session_start: show workspace binding status in the UI.
 * - before_agent_start (first turn only): inject workspace context —
 *   either the loaded brain (HANDOFF/TASKS pointers) or the workspace picker
 *   instruction (never default to cwd).
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

function buildContext(cwd: string): string {
  const brain = join(cwd, ".brain");
  const brainHome = join(cwd, ".brain-home");

  if (existsSync(brainHome)) {
    const ref = readFileSync(brainHome, "utf8").split("\n")[0].trim();
    return `[project-brains] 本项目的 brain 托管在别处: ${ref}。所有记录写到那边,本地不建 .brain/。`;
  }

  if (existsSync(brain)) {
    const lines = [`[project-brains] 工作空间: ${cwd} (已有 brain)`];
    const tasksFile = join(brain, "TASKS.md");
    if (existsSync(tasksFile)) {
      const body = readFileSync(tasksFile, "utf8");
      const useCheckbox = /^- \[ \]/m.test(body);
      const active = body
        .split("\n")
        .filter((l) => (useCheckbox ? /^- \[ \]/.test(l) : / active$/.test(l)));
      lines.push(`活跃任务 ${active.length} 个 (.brain/TASKS.md):`);
      lines.push(...active.slice(0, 10));
      if (active.length > 1) {
        lines.push('提示: 多个活跃任务。用户只说"继续"时,列出清单让用户选,不要自动挑。');
      }
    }
    lines.push("接手前先读 .brain/HANDOFF.md;遇到难题先查 .brain/wiki/index.md(若存在)。");
    return lines.join("\n");
  }

  const lines = [
    `[project-brains] 当前目录 ${cwd} 未绑定任何项目工作空间。`,
    "在开始开发类任务前,先问用户本次要开发哪个项目(纯问答/闲聊则无需问):",
  ];
  const registry = join(homedir(), ".project-brains", "registry.tsv");
  if (existsSync(registry)) {
    const rows = readFileSync(registry, "utf8")
      .split("\n")
      .filter(Boolean)
      .slice(0, 15)
      .map((r) => {
        const [path, name] = r.split("\t");
        return `  - ${name ?? path} (${path})`;
      });
    if (rows.length) lines.push("已登记项目:", ...rows);
  }
  lines.push(
    "  - 或用户指定一个本地目录路径",
    "  - 或用户指定一个 GitHub 仓库(clone 到 ~/projects/<名称>)",
    "不要默认把当前目录当工作空间。细节见 project-brains skill。",
  );
  return lines.join("\n");
}

export default function projectBrains(pi: ExtensionAPI) {
  let injected = false;

  pi.on("session_start", async (_event, ctx) => {
    const bound = existsSync(join(process.cwd(), ".brain"));
    ctx.ui.notify(
      bound
        ? "🧠 project-brains: 工作空间已绑定"
        : "🧠 project-brains: 未绑定工作空间,首个开发任务前会先询问项目",
      "info",
    );
  });

  pi.on("before_agent_start", async (_event, _ctx) => {
    if (injected) return;
    injected = true;
    return {
      message: {
        customType: "project-brains",
        content: buildContext(process.cwd()),
        display: true,
      },
    };
  });
}
