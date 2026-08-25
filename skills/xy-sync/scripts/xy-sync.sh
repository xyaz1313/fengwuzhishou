#!/usr/bin/env bash
# xy-sync：同步 XY 工作台。
#   sync         重建原子导出（tools/build_atoms.py）+ 用 xy-link 批量桥接 skills/ 到各宿主
#   git-check    判断本仓库能否安全 push：git 顶层必须 == 仓库根，且 knowledge/_internal、private 被忽略
#   push "<msg>" 只有 git-check 通过 + --yes 才提交并推送
#   pull         拉取后自动 sync
#   check-remote 读远端 UPDATE.json 比版本；24h 只查一次；任何失败静默（退出 0，无输出）
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "$here/../../.." && pwd -P)"          # skills/xy-sync/scripts → 仓库根
XY_HOME="${XY_HOME:-$HOME/.xy}"
BRIDGE="$ROOT/skills/xy-link/scripts/bridge-skill.sh"
BUILD="$ROOT/tools/build_atoms.py"

usage() {
  sed -n '2,8p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

# ---------- 阶段 A：本地同步 ----------
cmd_sync() {
  local before after new failed=0
  echo "== 仓库根：$ROOT"
  if [[ -f "$BUILD" ]]; then
    echo "== 重建原子导出（knowledge/atoms.jsonl + 各 skill references/）"
    python3 "$BUILD" >/dev/null 2>&1 && echo "✓ build_atoms 完成" || { echo "✗ build_atoms 失败（先自己跑一遍看报错：python3 tools/build_atoms.py）"; failed=1; }
  else
    echo "· 没有 tools/build_atoms.py，跳过原子导出"
  fi
  [[ -x "$BRIDGE" || -f "$BRIDGE" ]] || { echo "✗ 找不到 xy-link 脚本：$BRIDGE"; return 1; }
  before="$(ls "$HOME/.agents/skills" 2>/dev/null | sort || true)"
  echo "== 批量桥接 skills/ → 各宿主"
  mkdir -p "$XY_HOME" 2>/dev/null || true
  bash "$BRIDGE" link "$ROOT/skills" > "$XY_HOME/last_sync.log" 2>&1 || failed=1
  after="$(ls "$HOME/.agents/skills" 2>/dev/null | sort || true)"
  new="$(comm -13 <(printf '%s\n' "$before") <(printf '%s\n' "$after") | tr '\n' ' ')"
  echo "· 已桥接 skill 数：$(printf '%s\n' "$after" | grep -c . || true)"
  [[ -n "${new// /}" ]] && echo "· 本次新增入口：$new" || echo "· 无新增入口（已有软链重新确认）"
  grep '^✗' "$XY_HOME/last_sync.log" | sed 's/^/  /' || true
  echo "· 详细输出：$XY_HOME/last_sync.log"
  return "$failed"
}

# ---------- 阶段 B：git 安全判定 ----------
git_top() { git -C "$ROOT" rev-parse --show-toplevel 2>/dev/null; }

cmd_git_check() {
  local top remote
  top="$(git_top)" || { echo "NO_REPO：仓库根不在任何 git 仓库里"; return 10; }
  if [[ "$top" != "$ROOT" ]]; then
    echo "PARENT_REPO：git 顶层是 ${top}，不是仓库根 ${ROOT}。父目录建的仓库会把 knowledge/_internal、逐字稿、规划文档一起推出去——拒绝 push。"; return 11
  fi
  remote="$(git -C "$ROOT" remote get-url origin 2>/dev/null)" || { echo "NO_REMOTE：是 git 仓库但没有 origin"; return 12; }
  local p
  for p in knowledge/_internal private .private; do
    [[ -e "$ROOT/$p" ]] || continue
    if ! git -C "$ROOT" check-ignore -q "$p"; then echo "NOT_IGNORED：$p 没被 .gitignore 忽略，拒绝 push"; return 13; fi
    if [[ -n "$(git -C "$ROOT" ls-files "$p" 2>/dev/null)" ]]; then echo "TRACKED：$p 已被 git 跟踪，先移出索引再谈 push"; return 14; fi
  done
  echo "OK：顶层=${ROOT}，origin=${remote}，内部目录已忽略"
}

cmd_push() {
  local msg="${1:-}" yes="${2:-}"
  [[ -n "$msg" ]] || { echo "✗ 需要提交说明：push \"<msg>\" --yes"; return 1; }
  cmd_git_check || return $?
  [[ "$yes" == "--yes" ]] || { echo "== 将提交的改动："; git -C "$ROOT" status --short; echo "✗ 未加 --yes，未推送。让用户在当前对话确认后再跑。"; return 2; }
  git -C "$ROOT" add -A && git -C "$ROOT" commit -m "$msg" && git -C "$ROOT" push
}

cmd_pull() {
  cmd_git_check >/dev/null || { cmd_git_check; return $?; }
  git -C "$ROOT" pull --ff-only || return 1
  cmd_sync
}

# ---------- 阶段 C：远端版本检查（接 GitHub 后启用） ----------
# 远端地址从环境变量 XY_UPDATE_URL 或 ~/.xy/config.json 的 update_url 读；没有就静默退出。
cmd_check_remote() {
  local url stamp now local_ver remote_ver notice
  url="${XY_UPDATE_URL:-}"
  [[ -z "$url" && -f "$XY_HOME/config.json" ]] && url="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("update_url",""))' "$XY_HOME/config.json" 2>/dev/null || true)"
  [[ -n "$url" ]] || exit 0
  mkdir -p "$XY_HOME" 2>/dev/null || exit 0
  stamp="$XY_HOME/update_check_at"; now="$(date +%s)"
  if [[ -f "$stamp" ]] && (( now - $(cat "$stamp" 2>/dev/null || echo 0) < 86400 )); then exit 0; fi
  echo "$now" > "$stamp" 2>/dev/null || true
  local_ver="$(cat "$ROOT/VERSION" 2>/dev/null | tr -d '[:space:]')"
  read -r remote_ver notice < <(curl -fsSL --max-time 5 "$url" 2>/dev/null | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("version",""),d.get("notice",""))' 2>/dev/null) || exit 0
  [[ -n "$remote_ver" && -n "$local_ver" ]] || exit 0
  # 只在远端**严格更高**时才提醒：开发机版本领先线上时不能弹假警报（假警报比没警报更糟——
  # 第一次看见错的提示之后，用户会连真提醒一起无视）。逐段比较，不做字符串比较。
  version_is_higher() {   # $1 > $2 ?
    local a b; local -a A B
    IFS=. read -r -a A <<< "${1%%[-+]*}"; IFS=. read -r -a B <<< "${2%%[-+]*}"
    for i in 0 1 2; do
      a="${A[i]:-0}"; b="${B[i]:-0}"
      [[ "$a" =~ ^[0-9]+$ ]] || a=0; [[ "$b" =~ ^[0-9]+$ ]] || b=0
      (( a > b )) && return 0
      (( a < b )) && return 1
    done
    return 1   # 相等不算更高
  }
  version_is_higher "$remote_ver" "$local_ver" || exit 0
  echo "XY 有新版本 ${remote_ver}（当前 ${local_ver}）：$notice 回复 1 立即更新，或输入 /xy-sync。"
}

case "${1:-}" in
  sync)          cmd_sync ;;
  git-check)     cmd_git_check ;;
  push)          cmd_push "${2:-}" "${3:-}" ;;
  pull)          cmd_pull ;;
  check-remote)  cmd_check_remote ;;
  *)             usage; exit 1 ;;
esac
