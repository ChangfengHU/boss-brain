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
run() { printf '{"cwd":"%s","stop_hook_active":false,"session_id":"%s"}' "$1" "${2:-nosid}" | bash "$H/stop-evidence-check.sh" 2>&1; }

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

echo
echo "结果:$PASS 通过,$FAIL 失败"
[ "$FAIL" -eq 0 ]
