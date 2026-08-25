#!/usr/bin/env bash
# xy-link：把 skill 真源软链到本机已安装的宿主。
# 只做三件事：link / unlink / status。不复制文件，不建不存在的宿主目录，不动真实目录。
set -euo pipefail

usage() {
  cat <<'USAGE'
用法:
  bridge-skill.sh link   <skill 名 | 相对路径 | 绝对路径 | skill 集合目录>
  bridge-skill.sh unlink <同上>
  bridge-skill.sh status <同上>

例子:
  bridge-skill.sh link xy-selection          # 仓库 skills/xy-selection
  bridge-skill.sh link skills                # 整个 skills/ 目录批量桥接
  bridge-skill.sh link /abs/path/to/skill    # 外部 skill
  bridge-skill.sh status skills

宿主分三层:
  公共入口  ~/.agents/skills           总是写；Codex / Copilot / Gemini CLI / Cursor / Augment /
                                       Roo Code / OpenCode / OpenHands 都从这里读
  专属入口  ~/.claude ~/.workbuddy ~/.hermes ~/.kiro ~/.qwen ~/.cline ~/.trae ~/.trae-cn
            ~/.kimi-code ~/.kimi        宿主主目录已存在才写 <主目录>/skills/<name>
                                       (Kimi Code CLI 0.36 读 ~/.kimi-code/skills + ~/.agents/skills；
                                        ~/.kimi/skills 是旧版 kimi-cli 目录，存在才顺带链)
  悟空      无公开本地 skills 目录约定：只写公共入口 ~/.agents/skills，
            用户需在悟空客户端「技能中心」上传 SKILL.md/ZIP 或在设置里手动指定
  Grok      ~/.grok/skills/<name>/SKILL.md   薄 bridge（user_invocable: true），不是软链

永不桥接: private/ .private/ knowledge/_internal/
USAGE
}

die() { echo "✗ $*" >&2; exit 1; }

# 仓库根 = scripts/ 往上三层（skills/xy-link/scripts → 仓库根）
repo_root() {
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
  cd "$here/../../.." && pwd -P
}

# ---------- 宿主目录 ----------
SHARED_DIR="$HOME/.agents/skills"

# 专属入口：只在 <主目录> 已存在时才写 <主目录>/skills/<name>
NATIVE_DIRS=(
  "$HOME/.claude/skills"
  "$HOME/.workbuddy/skills"
  "$HOME/.hermes/skills"
  "$HOME/.kiro/skills"
  "$HOME/.qwen/skills"
  "$HOME/.cline/skills"
  "$HOME/.trae/skills"
  "$HOME/.trae-cn/skills"
  "$HOME/.kimi-code/skills" # Kimi Code CLI 0.36（本机实测 2026-08-18）：用户级 $KIMI_CODE_HOME/skills
                            #   （默认 ~/.kimi-code/skills）+ 通用 ~/.agents/skills；也认 --skills-dir
  "$HOME/.kimi/skills"      # 旧版 Python kimi-cli 1.x 的目录；kimi-code 首次运行会把它复制到 ~/.kimi-code/skills。
                            #   只在 ~/.kimi 已存在时顺带链一份，不新建
)
# 悟空（最可能是阿里/钉钉桌面客户端，待用户确认产品名）：未找到公开的本地 skills 目录约定，
#   官方通道是客户端「技能中心 → 上传技能」(SKILL.md / ZIP)。这里不为它建目录、不软链；
#   只靠公共入口 ~/.agents/skills，用户需在悟空里手动上传 ZIP 或在设置里指定目录。

# 旧入口：这些客户端已能读公共入口，早期脚本却往它们的专属目录写过软链。
# link 时若发现指向同一真源的旧软链就清掉，避免同一 skill 在 Codex 等端出现两次。
LEGACY_DIRS=(
  "$HOME/.codex/skills"
  "$HOME/.cursor/skills"
)

# ---------- 路径判定 ----------
# 永不桥接的源：仓库内 private/ .private/ knowledge/_internal/，以及任何名为 private/.private/_internal 的目录本身
is_forbidden_source() {
  local p="$1" root="$2"
  case "$p" in
    "$root/private"|"$root/private/"*|"$root/.private"|"$root/.private/"*|"$root/knowledge/_internal"|"$root/knowledge/_internal/"*) return 0 ;;
  esac
  case "$(basename "$p")" in
    private|.private|_internal) return 0 ;;
  esac
  return 1
}

resolve_candidate() {
  local input="$1" root="$2" c
  if [[ "$input" = /* ]]; then c="$input"
  elif [[ -d "$PWD/$input" ]]; then c="$PWD/$input"
  elif [[ -d "$root/$input" ]]; then c="$root/$input"
  elif [[ -d "$root/skills/$input" ]]; then c="$root/skills/$input"
  else die "找不到 skill 或 skill 集合目录：$input"
  fi
  [[ -d "$c" ]] || die "不是目录：$c"
  c="$(cd "$c" && pwd -P)"
  is_forbidden_source "$c" "$root" && die "拒绝桥接受保护目录：${c}（private/ .private/ knowledge/_internal/ 永不对外）"
  printf '%s\n' "$c"
}

# 输出一个或多个 skill 源目录（含 SKILL.md 的目录）
list_skill_sources() {
  local candidate="$1" root="$2" found=0 f d
  if [[ -f "$candidate/SKILL.md" ]]; then printf '%s\n' "$candidate"; return 0; fi
  while IFS= read -r f; do
    d="$(dirname "$f")"
    if is_forbidden_source "$d" "$root"; then echo "· 跳过受保护目录 $d" >&2; continue; fi
    found=1; printf '%s\n' "$d"
  done < <(find "$candidate" -mindepth 2 -maxdepth 2 -name SKILL.md -type f | sort)
  [[ "$found" -eq 1 ]] || die "$candidate 里没有 SKILL.md，一级子目录里也没有"
}

# 软链实际指向（解析成物理路径）；失败返回非 0
resolved_target() {
  local link="$1" t parent
  t="$(readlink "$link")" || return 1
  if [[ "$t" != /* ]]; then parent="$(dirname "$link")"; t="$parent/$t"; fi
  [[ -d "$t" ]] || return 1
  (cd "$t" && pwd -P)
}

# 该软链是否指向 src
points_to() {
  local link="$1" src="$2" t
  [[ -L "$link" ]] || return 1
  [[ "$(readlink "$link")" == "$src" ]] && return 0
  t="$(resolved_target "$link" 2>/dev/null || true)"
  [[ -n "$t" && "$t" == "$src" ]]
}

# 该软链是否指向 candidate 或其子目录（集合桥接后清理失效项用）
points_under() {
  local link="$1" base="$2" t
  [[ -L "$link" ]] || return 1
  case "$(readlink "$link")" in "$base"|"$base"/*) return 0 ;; esac
  t="$(resolved_target "$link" 2>/dev/null || true)"
  case "$t" in "$base"|"$base"/*) return 0 ;; esac
  return 1
}

# ---------- 软链动作 ----------
# link_one <src> <dest_dir> <name> <create_parent 0|1> <label>
link_one() {
  local src="$1" dest="$2" name="$3" create="$4" label="$5"
  local link host
  link="$dest/$name"
  host="$(dirname "$dest")"
  if [[ "$create" -eq 0 && ! -d "$host" ]]; then
    echo "· ${label}：$host 未安装，跳过"; return 0
  fi
  mkdir -p "$dest"
  if [[ -e "$link" && ! -L "$link" ]]; then
    echo "✗ ${label}：$link 是真实目录或文件，已保留"; return 2
  fi
  ln -sfn "$src" "$link"
  echo "✓ ${label}：$link -> $(readlink "$link")"
}

# unlink_one <src> <dest_dir> <name> <label>：只删指向 src 的软链
unlink_one() {
  local src="$1" dest="$2" name="$3" label="$4" link
  link="$dest/$name"
  if [[ -L "$link" ]]; then
    if points_to "$link" "$src"; then rm "$link"; echo "✓ ${label}：已移除 $link"
    else echo "✗ ${label}：$link 指向别的源（$(readlink "$link")），已保留"; return 2; fi
  elif [[ -e "$link" ]]; then
    echo "✗ ${label}：$link 是真实目录或文件，已保留"; return 2
  else
    echo "· ${label}：$link 不存在"
  fi
}

# status_one <src> <dest_dir> <name> <label>
status_one() {
  local src="$1" dest="$2" name="$3" label="$4" link
  link="$dest/$name"
  if [[ -L "$link" ]]; then
    if points_to "$link" "$src"; then echo "✓ ${label}：$link -> $(readlink "$link")"
    else echo "✗ ${label}：$link 指向别的源 $(readlink "$link")"; return 2; fi
  elif [[ -e "$link" ]]; then
    echo "✗ ${label}：$link 存在但不是软链"; return 2
  else
    echo "· ${label}：$link 未桥接"
  fi
}

# 旧入口清理 / 状态
legacy_clean_one() {
  local src="$1" dest="$2" name="$3" link
  link="$dest/$name"
  [[ -d "$dest" ]] || return 0
  if [[ -L "$link" ]] && points_to "$link" "$src"; then rm "$link"; echo "✓ 旧入口：已清理 ${link}（该宿主改读公共入口）"
  elif [[ -L "$link" ]]; then echo "✗ 旧入口：$link 指向别的源，已保留"; return 2
  elif [[ -e "$link" ]]; then echo "✗ 旧入口：$link 是真实目录或文件，已保留"; return 2
  fi
}
legacy_status_one() {
  local src="$1" dest="$2" name="$3" link
  link="$dest/$name"
  if [[ -L "$link" ]] && points_to "$link" "$src"; then echo "✗ 旧入口：$link 仍指向本源，重复入口，跑一次 link 可清理"; return 2
  elif [[ -L "$link" ]]; then echo "✗ 旧入口：$link 指向别的源 $(readlink "$link")"; return 2
  elif [[ -e "$link" ]]; then echo "✗ 旧入口：$link 存在真实目录或文件"; return 2
  fi
  return 0
}

# 集合桥接后：清掉指向集合内、但源已不存在的软链与 Grok bridge
clean_stale() {
  local base="$1" d link t g sf
  for d in "$SHARED_DIR" "${NATIVE_DIRS[@]}"; do
    [[ -d "$d" ]] || continue
    while IFS= read -r link; do
      points_under "$link" "$base" || continue
      t="$(readlink "$link")"
      [[ -f "$t/SKILL.md" ]] || { rm "$link"; echo "✓ 清理失效软链 $link"; }
    done < <(find "$d" -mindepth 1 -maxdepth 1 -type l | sort)
  done
  [[ -d "$HOME/.grok/skills" ]] || return 0
  while IFS= read -r g; do
    grep -q '^## Grok Bridge$' "$g" || continue
    sf="$(grep -m1 '^- Source of truth:' "$g" | sed 's/^- Source of truth: //')"
    case "$sf" in "$base"/SKILL.md|"$base"/*/SKILL.md)
      [[ -f "$sf" ]] || { rm -rf "$(dirname "$g")"; echo "✓ 清理失效 Grok bridge $(dirname "$g")"; } ;;
    esac
  done < <(find "$HOME/.grok/skills" -mindepth 2 -maxdepth 2 -name SKILL.md -type f | sort)
}

# ---------- Grok 薄 bridge ----------
grok_link() {
  local src="$1" name="$2" dir sf
  dir="$HOME/.grok/skills/$name"; sf="$dir/SKILL.md"
  [[ -d "$HOME/.grok" ]] || { echo "· Grok：~/.grok 未安装，跳过"; return 0; }
  if [[ -L "$dir" ]]; then rm "$dir"
  elif [[ -e "$dir" && ! -d "$dir" ]]; then echo "✗ Grok：$dir 是真实文件，已保留"; return 2
  elif [[ -d "$dir" && -f "$sf" ]] && ! grep -q '^## Grok Bridge$' "$sf"; then echo "✗ Grok：$dir 是真实 Grok skill，已保留"; return 2
  elif [[ -d "$dir" && ! -f "$sf" ]]; then echo "✗ Grok：$dir 是真实目录，已保留"; return 2
  fi
  mkdir -p "$dir"
  cat > "$sf" <<EOF
---
name: $name
user_invocable: true
description: |
  $name 的 Grok 入口。在 Grok TUI 输入 /$name 触发；触发后先读取下方真源 SKILL.md，再按真源执行。
---
# $name

## Grok Bridge

- Source of truth: $src/SKILL.md
- 先读真源，再动手；流程、约束、输出格式全部以真源为准。
- 本文件只是入口指针，不在这里维护任何逻辑；要改就改真源。

## 使用说明

1. Grok TUI 里输入 \`/$name\`。
2. 真源更新后无需重建本文件（路径不变即可）。
EOF
  echo "✓ Grok：$dir -> $src"
}
grok_unlink() {
  local name="$1" dir sf
  dir="$HOME/.grok/skills/$name"; sf="$dir/SKILL.md"
  [[ -d "$HOME/.grok" ]] || { echo "· Grok：~/.grok 未安装，跳过"; return 0; }
  if [[ -L "$dir" ]]; then rm "$dir"; echo "✓ Grok：已移除软链 $dir"
  elif [[ -d "$dir" && -f "$sf" ]] && grep -q '^## Grok Bridge$' "$sf"; then rm -rf "$dir"; echo "✓ Grok：已移除 bridge $dir"
  elif [[ -e "$dir" ]]; then echo "✗ Grok：$dir 不是本工具生成的 bridge，已保留"; return 2
  else echo "· Grok：$dir 不存在"; fi
}
grok_status() {
  local src="$1" name="$2" dir sf s
  dir="$HOME/.grok/skills/$name"; sf="$dir/SKILL.md"
  [[ -d "$HOME/.grok" ]] || { echo "· Grok：~/.grok 未安装"; return 0; }
  if [[ -d "$dir" && -f "$sf" ]] && grep -q '^## Grok Bridge$' "$sf"; then
    s="$(grep -m1 '^- Source of truth:' "$sf" | sed 's/^- Source of truth: //')"
    if ! grep -q '^user_invocable: true$' "$sf"; then echo "✗ Grok：$dir 缺 user_invocable: true"; return 2; fi
    if [[ "$s" != "$src/SKILL.md" ]]; then echo "✗ Grok：$dir 指向别的源 $s"; return 2; fi
    echo "✓ Grok：$dir -> $s"
  elif [[ -e "$dir" ]]; then echo "✗ Grok：$dir 存在但不是 xy-link 生成的 bridge"; return 2
  else echo "· Grok：$dir 未桥接"; fi
}

# ---------- 主流程 ----------
main() {
  [[ $# -eq 2 ]] || { usage; exit 1; }
  local action="$1" input="$2" root candidate src name d failed=0
  case "$action" in link|unlink|status) ;; *) usage; exit 1 ;; esac

  root="$(repo_root)"
  candidate="$(resolve_candidate "$input" "$root")"

  while IFS= read -r src; do
    name="$(basename "$src")"
    echo "== $name =="
    case "$action" in
      link)
        link_one "$src" "$SHARED_DIR" "$name" 1 "公共入口" || failed=1
        for d in "${NATIVE_DIRS[@]}"; do link_one "$src" "$d" "$name" 0 "专属入口" || failed=1; done
        for d in "${LEGACY_DIRS[@]}"; do legacy_clean_one "$src" "$d" "$name" || failed=1; done
        grok_link "$src" "$name" || failed=1
        ;;
      unlink)
        unlink_one "$src" "$SHARED_DIR" "$name" "公共入口" || failed=1
        for d in "${NATIVE_DIRS[@]}" "${LEGACY_DIRS[@]}"; do
          [[ -d "$d" ]] || continue
          unlink_one "$src" "$d" "$name" "专属入口" || failed=1
        done
        grok_unlink "$name" || failed=1
        ;;
      status)
        status_one "$src" "$SHARED_DIR" "$name" "公共入口" || failed=1
        for d in "${NATIVE_DIRS[@]}"; do
          [[ -d "$(dirname "$d")" ]] && { status_one "$src" "$d" "$name" "专属入口" || failed=1; }
        done
        for d in "${LEGACY_DIRS[@]}"; do legacy_status_one "$src" "$d" "$name" || failed=1; done
        grok_status "$src" "$name" || failed=1
        ;;
    esac
  done < <(list_skill_sources "$candidate" "$root")

  [[ "$action" == "link" ]] && clean_stale "$candidate"
  [[ "$action" == "status" && "$failed" -eq 0 ]] && echo "✓ 全部入口指向正确，无重复入口"
  exit "$failed"
}

main "$@"
