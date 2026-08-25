#!/usr/bin/env bash
# project-brains 回归自测:按「承诺」而不是按实现写断言。
#
#   bash ~/.project-brains/selftest.sh
#
# brain 的原始目的:让项目的连续性不依赖任何会话的记忆。
# 换会话、换机器、换人,凭落盘的东西就能完整接手。下面每一节对应一句承诺。
set -u
SRC="$(cd "$(dirname "$0")" && pwd)"
H="$SRC/hooks"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  FAIL %s\n     %s\n' "$1" "${2:-}"; }
blocked()   { printf '%s' "$1" | grep -q '"decision": *"block"' ; }
say_block() { if blocked "$2"; then ok "$1"; else bad "$1" "应当拦截,实际放行:${2:0:120}"; fi; }
say_pass()  { if blocked "$2"; then bad "$1" "应当放行,实际拦截:${2:0:160}"; else ok "$1"; fi; }

mkrepo() { # $1=名字 → 建一个带 .brain 的 git 工作空间,返回路径
  d="$T/$1"; mkdir -p "$d/.brain/dev-log"
  git -C "$d" init -q; git -C "$d" config user.email t@t; git -C "$d" config user.name t
  # 合规工作空间自带真实的能力声明(gate5);缺失/模板未改的情形由承诺 10 显式构造
  printf 'provides\ttest.thing\t-\t测试夹具能力\n' > "$d/.brain/capabilities.tsv"
  echo x > "$d/code.txt"; git -C "$d" add -A >/dev/null; git -C "$d" commit -qm "work" >/dev/null
  printf '%s' "$d"
}
ev() { # $1=仓库 $2=wiki 字段值 → 写一条证据
  printf '{"date":"2026-01-01","task":"t","summary":"s","files":["f"],"verify":"cmd → 输出 x","exit":0,"risks":"r","wiki":"%s"}\n' \
    "$2" > "$1/.brain/evidence.jsonl"
  echo "记录" > "$1/.brain/dev-log/2026-01-01.md"
}
card() { # $1=仓库 → 写一张状态卡
  printf '# 状态卡\n## 定位\nx\n## 现状\nx\n## 下一步\n1. x\n## 阻塞\n无\n## 关键路径\nx\n## 雷区\n无\n' > "$1/.brain/STATE.md"
}
commit_brain() {
  # 与真实纪律一致:收工 commit 前刷新状态卡 mtime。否则当 commit 恰好跨秒时,
  # gate4 会因「状态卡(上一秒)比最新 commit(这一秒)旧」闪烁误拦 —— 实测约 1/10 概率。
  [ -f "$1/.brain/STATE.md" ] && touch "$1/.brain/STATE.md"
  git -C "$1" add -A >/dev/null 2>&1; git -C "$1" commit -qm "docs(brain)" >/dev/null 2>&1
}
# 门禁比的是秒级时间戳,而夹具里所有事都发生在同一秒内 —— 同秒时它分不出先后
# (这是 1 秒粒度的固有限制,不是 bug:真实场景里两次 commit 不会同秒)。
# 所以「工作 commit 晚于 brain 记录」这件事必须显式造出来,不能靠执行顺序。
work_commit_later() { # $1=仓库 $2=消息 $3=推后几秒
  echo "more-$RANDOM" >> "$1/code.txt"; git -C "$1" add -A >/dev/null
  GIT_AUTHOR_DATE="$(date -d "+${3:-120} seconds" +%s) +0000" \
  GIT_COMMITTER_DATE="$(date -d "+${3:-120} seconds" +%s) +0000" \
    git -C "$1" commit -qm "$2" >/dev/null
}
# run() 默认"认领"该仓(写 boss-touched 标记)= 模拟真实工作流:会话确实在这个仓干活。
# 未认领的"路过"场景由承诺 15 用 run_raw 单测。
mark() { mkdir -p /tmp/project-brains; grep -qxF "$1" "/tmp/project-brains/boss-touched-$2" 2>/dev/null || printf '%s\n' "$1" >> "/tmp/project-brains/boss-touched-$2"; }
run() { mark "$1" "${2:-nosid}"; printf '{"cwd":"%s","stop_hook_active":false,"session_id":"%s"}' "$1" "${2:-nosid}" | bash "$H/stop-evidence-check.sh" 2>&1; }
run_raw() { printf '{"cwd":"%s","stop_hook_active":false,"session_id":"%s"}' "$1" "${2:-nosid}" | bash "$H/stop-evidence-check.sh" 2>&1; }
rm -f /tmp/project-brains/boss-touched-nosid   # 清上次残留,避免跨 run 污染

echo "== 承诺 0:测的必须是线上跑的(src 与已安装副本无漂移)=="
# 2026-08-23 真踩过:改了 src/hooks 忘同步 hooks/,自测全绿但改动根本没生效。
for f in stop-evidence-check.sh session-start.sh codex-session-start.sh; do
  [ -f "$SRC/src/hooks/$f" ] || continue
  diff -q "$SRC/src/hooks/$f" "$H/$f" >/dev/null 2>&1 \
    && ok "hooks/$f 无漂移" || bad "hooks/$f 无漂移" "src/hooks 与已安装副本不同,同步后再测"
done
if [ -f "$HOME/.claude/skills/project-brains/SKILL.md" ]; then
  diff -q "$SRC/src/skill/project-brains/SKILL.md" "$HOME/.claude/skills/project-brains/SKILL.md" >/dev/null 2>&1 \
    && ok "SKILL.md 无漂移" || bad "SKILL.md 无漂移" "src 与 ~/.claude/skills 副本不同,同步后再测"
fi
# codex 侧同样是"线上跑的"——2026-08-25 审计:codex 副本停在旧版(缺 gate5 整章)而自测仍全绿,
# 正是 2026-08-23 同款事故换了个目录再犯。skill/prompts/宪法/版本文件一并盯住。
if [ -d "$HOME/.codex" ]; then
  diff -q "$SRC/src/skill/project-brains/SKILL.md" "$HOME/.codex/skills/project-brains/SKILL.md" >/dev/null 2>&1 \
    && ok "codex SKILL.md 无漂移" || bad "codex SKILL.md 无漂移" "重跑 src/install.sh 同步 codex 副本"
  for c in "$SRC/src/commands/"*.md; do
    b="$(basename "$c")"
    [ -f "$HOME/.codex/prompts/$b" ] || { bad "codex prompts/$b 无漂移" "未安装"; continue; }
    diff -q "$c" "$HOME/.codex/prompts/$b" >/dev/null 2>&1 \
      && ok "codex prompts/$b 无漂移" || bad "codex prompts/$b 无漂移" "重跑 src/install.sh 同步"
  done
  grep -qF "立即 push" "$HOME/.codex/AGENTS.md" 2>/dev/null \
    && ok "codex 宪法含现行 push 政策" || bad "codex 宪法含现行 push 政策" "AGENTS.md 宪法块是旧版"
  # 第三条分发通道:codex 命令 skill(installer 生成 frontmatter,正文必须等于 src 去掉 frontmatter)
  # 生成器会在 frontmatter 后多一个空行,比较时剥掉头部空行
  strip_fm() { awk 'NR==1&&/^---$/{f=1;next} f&&/^---$/{f=0;next} !f' "$1" | sed '/./,$!d'; }
  for c in "$SRC/src/commands/"*.md; do
    n="$(basename "$c" .md)"
    [ -f "$HOME/.codex/skills/$n/SKILL.md" ] || { bad "codex 命令skill/$n 无漂移" "未安装"; continue; }
    [ "$(strip_fm "$c")" = "$(strip_fm "$HOME/.codex/skills/$n/SKILL.md")" ] \
      && ok "codex 命令skill/$n 无漂移" || bad "codex 命令skill/$n 无漂移" "正文与 src 不同,重跑 src/install.sh"
  done
fi
# 旧 push 文案全域清零(2026-08-25 二轮:上一轮"统一"漏了 SKILL:152 与 takeover 一族)
if grep -rn "push 前先征得\|push 仍需用户同意\|push 需用户同意\|征询用户同意再 push\|push 必须先获得用户" \
     "$SRC/src" "$HOME/.claude/skills/project-brains" "$HOME/.claude/commands" \
     "$HOME/.codex/skills" "$HOME/.codex/prompts" >/dev/null 2>&1; then
  bad "push 旧文案清零" "$(grep -rln 'push 前先征得\|push 仍需用户同意\|push 需用户同意\|征询用户同意再 push\|push 必须先获得用户' "$SRC/src" "$HOME/.claude/skills/project-brains" "$HOME/.claude/commands" "$HOME/.codex/skills" "$HOME/.codex/prompts" 2>/dev/null | head -3)"
else
  ok "push 旧文案清零(src+四个安装面)"
fi
[ "$(cat "$HOME/.project-brains/version" 2>/dev/null)" = "$(cat "$SRC/src/VERSION" 2>/dev/null)" ] \
  && ok "version 记账与 src/VERSION 一致" || bad "version 记账与 src/VERSION 一致" "重跑 src/install.sh"

echo "== 承诺 1:有 commit 就必须有证据记录 =="
R="$(mkrepo p1)"
say_block "有 commit 无证据 → 拦截" "$(run "$R")"
ev "$R" none; card "$R"; commit_brain "$R"
say_pass  "补齐证据与状态卡后 → 放行" "$(run "$R")"

echo "== 承诺 2:证据必须回答「有没有值得沉淀的教训」 =="
R="$(mkrepo p2)"; card "$R"
printf '{"date":"2026-01-01","task":"t","summary":"s","verify":"v","exit":0}\n' > "$R/.brain/evidence.jsonl"
echo r > "$R/.brain/dev-log/2026-01-01.md"; commit_brain "$R"
say_block "证据缺 wiki 字段 → 拦截" "$(run "$R")"
ev "$R" none; commit_brain "$R"
say_pass  "补上 wiki 判断后 → 放行" "$(run "$R")"

echo "== 承诺 3:下一个会话 30 秒知道停在哪(状态卡)=="
R="$(mkrepo p3)"; ev "$R" none; commit_brain "$R"
say_block "有 commit 但没有状态卡 → 拦截" "$(run "$R")"
card "$R"; commit_brain "$R"
say_pass  "补上状态卡 → 放行" "$(run "$R")"
# 状态卡比工作 commit 旧 → 必须拦(过期的卡比没有卡更危险)
work_commit_later "$R" "新活" 120
git -C "$R" log -1 --format=%ct | grep -q . || bad "夹具:新活 commit 存在" "没造出来"
say_block "状态卡比新 commit 旧 → 拦截" "$(run "$R")"

echo "== 承诺 4:brain 的写入必须收口,不留脏文件 =="
R="$(mkrepo p4)"; ev "$R" none; card "$R"; commit_brain "$R"
echo "半截" > "$R/.brain/wiki-draft.md"
say_block ".brain/ 有未提交写入 → 拦截" "$(run "$R")"
commit_brain "$R"
say_pass  "收口后 → 放行" "$(run "$R")"

# 4b:没有工作 commit 的会话(纯问答里「记下来」)写了 .brain 也必须收口
R="$(mkrepo p4b)"; ev "$R" none; card "$R"; commit_brain "$R"
SID4="sess4-$RANDOM"; mkdir -p /tmp/project-brains
printf '%s %s\n' "$R" "$(git -C "$R" rev-parse HEAD)" > "/tmp/project-brains/session-$SID4.head"
echo "词条" > "$R/.brain/wiki-note.md"
say_block "无 commit 会话写 .brain 未提交 → 拦截" "$(run "$R" "$SID4")"
commit_brain "$R"
say_pass  "收口后 → 放行" "$(run "$R" "$SID4")"
rm -f "/tmp/project-brains/session-$SID4.head"

echo "== 承诺 5:不是 brain 工作空间就完全不打扰 =="
mkdir -p "$T/plain"; git -C "$T/plain" init -q
git -C "$T/plain" config user.email t@t; git -C "$T/plain" config user.name t
echo x > "$T/plain/f"; git -C "$T/plain" add -A >/dev/null; git -C "$T/plain" commit -qm x >/dev/null
O="$(run "$T/plain")"; { [ -z "$O" ] && ! blocked "$O"; } && ok "无 .brain 的 git 仓库静默放行" || bad "无 .brain 的 git 仓库静默放行" "$O"
mkdir -p "$T/nogit"
O="$(run "$T/nogit")"; [ -z "$O" ] && ok "非 git 目录静默放行" || bad "非 git 目录静默放行" "$O"

echo "== 承诺 6:并发会话不背别人的锅 =="
R="$(mkrepo p6)"; ev "$R" none; card "$R"; commit_brain "$R"
SID="sess-$RANDOM"; mkdir -p /tmp/project-brains
printf '%s %s\n' "$R" "$(git -C "$R" rev-parse HEAD)" > "/tmp/project-brains/session-$SID.head"
say_pass "本会话基线之后没提交 → 放行" "$(run "$R" "$SID")"
work_commit_later "$R" "基线之后的活" 120
say_block "基线之后有提交 → 按本会话追责" "$(run "$R" "$SID")"
rm -f "/tmp/project-brains/session-$SID.head"

echo "== 承诺 7:门禁不会把会话锁死 =="
R="$(mkrepo p7)"
O="$(printf '{"cwd":"%s","stop_hook_active":true,"session_id":"x"}' "$R" | bash "$H/stop-evidence-check.sh" 2>&1)"
say_pass "已经拦过一次(stop_hook_active)→ 直接放行,不死循环" "$O"

echo "== 承诺 8:开场就把「我在哪个项目」交给 agent =="
R="$(mkrepo p8)"; card "$R"
O="$(printf '{"cwd":"%s","session_id":"s8"}' "$R" | HOME="$T" bash "$H/session-start.sh" 2>&1)"
printf '%s' "$O" | grep -q "project-brains" && ok "在 brain 工作空间输出上下文" || bad "在 brain 工作空间输出上下文" "$O"
[ -f "/tmp/project-brains/session-s8.head" ] && ok "记录本会话基线 HEAD" || bad "记录本会话基线 HEAD" "基线文件没写"
rm -f /tmp/project-brains/session-s8.head
mkdir -p "$T/home2/.boss"
printf '%s\tp8\t别名\t一句话定位\tlocal\n' "$R" > "$T/home2/.boss/registry.tsv"
O="$(printf '{"cwd":"%s","session_id":"s8b"}' "$T/nogit" | HOME="$T/home2" bash "$H/session-start.sh" 2>&1)"
printf '%s' "$O" | grep -q "p8" && ok "未绑定目录时列出 boss 登记的项目" || bad "未绑定目录时列出 boss 登记的项目" "$O"
rm -f /tmp/project-brains/session-s8b.head

echo "== 承诺 9:托管型项目不在本地建 .brain =="
mkdir -p "$T/ref"; git -C "$T/ref" init -q
echo "/elsewhere/.brain" > "$T/ref/.brain-home"
O="$(printf '{"cwd":"%s","session_id":"s9"}' "$T/ref" | HOME="$T" bash "$H/session-start.sh" 2>&1)"
printf '%s' "$O" | grep -q "托管在别处" && ok "指针项目给出托管提示" || bad "指针项目给出托管提示" "$O"
[ -d "$T/ref/.brain" ] && bad "指针项目不建本地 .brain" "本地建了 .brain" || ok "指针项目不建本地 .brain"

echo "== 承诺 10:能力声明不写、不改就不许收工(boss 能力图的地基)=="
R="$(mkrepo p10)"; ev "$R" none; card "$R"; commit_brain "$R"
rm -f "$R/.brain/capabilities.tsv"; git -C "$R" add -A >/dev/null; git -C "$R" commit -qm "去掉声明" >/dev/null
say_block "有 commit 但没有能力声明 → 拦截" "$(run "$R")"
printf '# 模板\nprovides\texample.thing\thttps://example.com\t这里换成真的\n' > "$R/.brain/capabilities.tsv"
commit_brain "$R"
say_block "声明还是原样模板(含占位)→ 拦截" "$(run "$R")"
printf 'provides\treal.thing\t-\t真实声明\n' > "$R/.brain/capabilities.tsv"
commit_brain "$R"
say_pass  "换成真实声明后 → 放行" "$(run "$R")"

echo "== 承诺 11:只提交状态卡骗不过证据门禁(2026-08-25 收洞)=="
# 旧实现把"最后一个碰 .brain 的 commit"当证据时间戳:补一个 STATE-only commit
# 就能让零证据的工作 commit 溜过 gate1。现在只认证据文件本身的 commit。
R="$(mkrepo p11)"; ev "$R" none; card "$R"; commit_brain "$R"
work_commit_later "$R" "工作提交" 120
echo "改现状" >> "$R/.brain/STATE.md"
git -C "$R" add .brain/STATE.md >/dev/null
GIT_AUTHOR_DATE="$(date -d '+240 seconds' +%s) +0000" GIT_COMMITTER_DATE="$(date -d '+240 seconds' +%s) +0000" \
  git -C "$R" commit -qm "只动状态卡" >/dev/null
say_block "STATE-only commit 不能顶掉证据新鲜度 → 仍拦截" "$(run "$R")"

echo "== 承诺 11b:merge 提交穿不透证据门禁(2026-08-25 二轮收洞)=="
# git 历史简化会让 `log -1 -- pathspec` 对 merge 返回被合分支的旧时间戳:
# 证据(1 天前)"新于"它 → gate1/gate4 双穿透。现改为基线树 diff 判工作、无 pathspec 取时间戳。
R="$(mkrepo p11b)"
git -C "$R" checkout -qb feat
echo feat > "$R/feat.txt"; git -C "$R" add -A >/dev/null
GIT_AUTHOR_DATE="$(date -d '-2 days' +%s) +0000" GIT_COMMITTER_DATE="$(date -d '-2 days' +%s) +0000" \
  git -C "$R" commit -qm "旧分支工作" >/dev/null
git -C "$R" checkout -q -
ev "$R" none; card "$R"
git -C "$R" add -A >/dev/null
GIT_AUTHOR_DATE="$(date -d '-1 day' +%s) +0000" GIT_COMMITTER_DATE="$(date -d '-1 day' +%s) +0000" \
  git -C "$R" commit -qm "docs(brain)" >/dev/null
# 证据/状态卡必须"真旧":文件 mtime 也在门禁判据里,不回拨的话夹具全在同一秒,复现不了穿透
touch -d '-1 day' "$R/.brain/evidence.jsonl" "$R/.brain/STATE.md" "$R/.brain/dev-log/2026-01-01.md" 2>/dev/null
SIDM="st-merge-$RANDOM"; mkdir -p /tmp/project-brains
printf '%s %s\n' "$R" "$(git -C "$R" rev-parse HEAD)" > "/tmp/project-brains/session-$SIDM.head"
git -C "$R" merge -q --no-ff -m "merge feat" feat >/dev/null 2>&1
say_block "会话内 merge 带入代码且证据更旧 → 拦截" "$(run "$R" "$SIDM")"
rm -f "/tmp/project-brains/session-$SIDM.head"

echo "== 承诺 12:compact/resume 不重置会话基线(2026-08-25 收洞)=="
R="$(mkrepo p12)"; SID="st-base-$RANDOM"
ss() { printf '{"cwd":"%s","session_id":"%s"}' "$R" "$SID" | bash "$H/session-start.sh" >/dev/null 2>&1; }
ss; B1="$(cat "/tmp/project-brains/session-$SID.head")"
echo y >> "$R/code.txt"; git -C "$R" add -A >/dev/null; git -C "$R" commit -qm mid >/dev/null
ss   # 模拟 compact 再次触发 SessionStart
B2="$(cat "/tmp/project-brains/session-$SID.head")"
[ "$B1" = "$B2" ] && ok "同一会话基线只写一次,compact 不覆盖" || bad "同一会话基线只写一次,compact 不覆盖" "基线被重写:$B1 → $B2"
rm -f "/tmp/project-brains/session-$SID.head"

echo "== 承诺 13:开场注入文本干净(TASKS.md 零活跃任务不出垃圾行)=="
R="$(mkrepo p13)"; printf '# 任务\n- [x] 已完成的任务\n' > "$R/.brain/TASKS.md"
O="$(printf '{"cwd":"%s","session_id":"st-clean"}' "$R" | bash "$H/session-start.sh" 2>&1)"
printf '%s' "$O" | grep -q "活跃任务 0 个" && ok "零活跃任务时输出 0 个" || bad "零活跃任务时输出 0 个" "$O"
printf '%s' "$O" | grep -qE "integer expression|^0$" && bad "无垃圾行/无报错" "$O" || ok "无垃圾行/无报错"

echo "== 承诺 14:含空格路径的工作空间门禁照常生效(2026-08-25 二轮收洞)=="
mkdir -p "$T/my proj"; d="$T/my proj"
git -C "$d" init -q; git -C "$d" config user.email t@t; git -C "$d" config user.name t
mkdir -p "$d/.brain"; echo x > "$d/code.txt"; git -C "$d" add -A >/dev/null; git -C "$d" commit -qm work >/dev/null
SIDS="st-space-$RANDOM"; printf '%s %s\n' "$d" "$(git -C "$d" rev-parse HEAD)" > "/tmp/project-brains/session-$SIDS.head"
echo more >> "$d/code.txt"; git -C "$d" add -A >/dev/null
GIT_AUTHOR_DATE="$(date -d '+120 seconds' +%s) +0000" GIT_COMMITTER_DATE="$(date -d '+120 seconds' +%s) +0000" \
  git -C "$d" commit -qm work2 >/dev/null
say_block "空格路径 + 有 commit 无证据 → 仍拦截" "$(run "$d" "$SIDS")"
rm -f "/tmp/project-brains/session-$SIDS.head"

echo "== 承诺 15:cd 路过别人的仓不背锅(2026-08-25 任务漂移专项)=="
# 本会话没在这个仓开场(无基线)也没 @ 认领过它 → 即使它有无证据的新 commit,也放行——
# 那是别的会话的在途工作,替人写状态卡/证据 = 任务漂移 + 踩乱别人工作区。
R="$(mkrepo p15)"   # 有 commit、零证据:若被认领必拦
SIDF="st-foreign-$RANDOM"
O="$(run_raw "$R" "$SIDF")";
say_pass "无基线且未认领 → 路过放行" "$O"
mark "$R" "$SIDF"
say_block "同一仓一旦认领 → 照常拦" "$(run_raw "$R" "$SIDF")"
rm -f "/tmp/project-brains/boss-touched-$SIDF"

echo
echo "结果:$PASS 通过,$FAIL 失败"
[ "$FAIL" -eq 0 ]
