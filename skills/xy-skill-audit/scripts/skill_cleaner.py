#!/usr/bin/env python3
"""本地 skill 的只读审查与可恢复隔离工具。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# 默认扫描的宿主目录：Claude Code / Codex / 公共入口 / WorkBuddy / Grok（不存在的目录自动跳过）
DEFAULT_ROOTS = [Path.home() / name / "skills" for name in (".claude", ".codex", ".agents", ".workbuddy", ".grok")]
QUARANTINE_ROOT = Path.home() / ".xy" / "skill-cleaner" / "quarantine"
EXECUTABLE_SUFFIXES = {".py", ".sh", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".rb", ".pl"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", "docs", "references", "assets", "tests", "test", "evals"}
ORDER = {"严重": 0, "高风险": 1, "待复核": 2, "信息": 3}
SELF_NAME = "xy-skill-audit"

# 商业词分两级。强导流词：出现就至少"待复核"；弱业务词：私域/课程/咨询类 skill 天天用，
# 只有和"每次回复 / 所有输出 / 隐藏 / 不得披露"这类强制或隐瞒语境共现时才升级，否则不计。
COMMERCIAL_STRONG = r"(?:加微信|添加微信|加我微信|扫码加|付费解锁|推广链接|联盟链接|带货链接|返佣)"
COMMERCIAL_WEAK = r"(?:微信号|课程|咨询|购买|下单|佣金|报名|付费)"
COMMERCIAL = r"(?:" + COMMERCIAL_STRONG + r"|" + COMMERCIAL_WEAK + r")"
FORCED = r"(?:每次|所有|任何|每一条).{0,40}(?:回复|回答|输出|结尾).{0,60}" + COMMERCIAL + r"|(?:无论|不管).{0,40}(?:用户|任务).{0,60}" + COMMERCIAL
COVERT = r"(?:隐藏|不要披露|不得披露|不得告知|不要告诉用户|伪装|悄悄).{0,60}" + COMMERCIAL + r"|" + COMMERCIAL + r".{0,60}(?:隐藏|不要披露|不得披露|不得告知|不要告诉用户|伪装|悄悄)"
SENSITIVE = r"(?:cookie(?:s)?|浏览器(?:\s*)凭据|凭据|密钥|私钥|密码|token|环境变量)"
NETWORK = r"(?:curl|wget|fetch\s*\(|axios|requests\.|webhook|http(?:s)?://|上传|发送|传输|外传)"
# 否定语境：这些词出现在命中词前后 20 字内，说明文本是在禁止/排除该行为，不计。
NEGATION = r"(?:不读取|不读|不得|不能|不要|不会|不允许|不上传|不联网|不执行|不发送|不外传|不把|不碰|禁止|拒绝|排除|默认跳过|跳过|永不|绝不|严禁|忌|红线|违规|警告|反面|误报)"
# 原子 id 形态（SCP-013 / XSP-028）不算 scp / nc 命令
ATOM_ID = re.compile(r"[A-Za-z]{2,4}-\d{3,4}")


def line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def excerpt(text: str, index: int) -> str:
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    return " ".join(text[start:len(text) if end < 0 else end].strip().split())[:240]


def finding(rule: str, severity: str, principle: str, message: str, path: Path, content: str, index: int) -> dict:
    return {"rule": rule, "severity": severity, "principle": principle, "message": message,
            "file": str(path), "line": line_number(content, index), "excerpt": excerpt(content, index)}


def scanned_files(skill_dir: Path):
    """只读取入口说明与可能被执行的代码，刻意跳过文档、变更记录和测试。"""
    for path in skill_dir.rglob("*"):
        # 只排除 skill 内部的文档与测试目录。用户显式传入的根目录即便位于
        # tests/ 下，也必须能够作为回归样本被扫描。
        if any(part in SKIP_DIRS for part in path.relative_to(skill_dir).parts):
            continue
        if not path.is_file() or path.stat().st_size > 1_000_000:
            continue
        if path.name == "SKILL.md" or path.suffix.lower() in EXECUTABLE_SUFFIXES:
            yield path


def skill_fingerprint(skill_dir: Path) -> str:
    """用于合并同一 skill 的多端镜像；仅以入口及可执行文件为依据。"""
    digest = hashlib.sha256()
    for path in sorted(scanned_files(skill_dir), key=lambda item: str(item.relative_to(skill_dir))):
        try:
            digest.update(str(path.relative_to(skill_dir)).encode())
            digest.update(path.read_bytes())
        except OSError:
            pass
    return digest.hexdigest()


def iter_skill_md(root: Path):
    """递归查找 SKILL.md，主动跟随符号链接目录。

    pathlib 的 rglob 在做 ** 递归时默认不会进入符号链接目录，而 xy-link
    安装的每一个 skill 在 ~/.claude/skills 等宿主目录下都是符号链接——如果
    不主动跟随，扫描器会看不到任何一个通过 xy-link 桥接的 skill。用已解析
    路径的集合防止符号链接成环导致无限递归。
    """
    seen_dirs: set[Path] = set()
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            real = current.resolve()
        except OSError:
            continue
        if real in seen_dirs:
            continue
        seen_dirs.add(real)
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        skill_md = current / "SKILL.md"
        if skill_md.is_file():
            yield skill_md
        for entry in entries:
            if entry.name in SKIP_DIRS:
                continue
            if entry.is_dir():
                stack.append(entry)


def find_skills(roots: list[Path]) -> tuple[list[Path], int]:
    """按真实路径和内容指纹去重，避免软链、多端镜像和内嵌副本重复计数。"""
    candidates: list[Path] = []
    seen_real: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for marker in iter_skill_md(root):
            candidate = marker.parent
            try:
                real = candidate.resolve()
            except OSError:
                real = candidate.absolute()
            if real not in seen_real:
                candidates.append(candidate)
                seen_real.add(real)
    # 精确相同的入口与执行代码通常是同一 skill 的多端副本，报告一次即可。
    found: list[Path] = []
    seen_content: set[str] = set()
    duplicates = 0
    for candidate in sorted(candidates, key=str):
        fingerprint = skill_fingerprint(candidate)
        if fingerprint in seen_content:
            duplicates += 1
            continue
        found.append(candidate)
        seen_content.add(fingerprint)
    return found, duplicates + len(candidates) - len({str(path.resolve()) for path in candidates})


def has_consent(window: str) -> bool:
    return bool(re.search(r"(?:用户|你)(?:明确|主动)?(?:要求|请求|询问|问到|提出|授权|同意|需要)|在用户(?:明确|主动)?(?:要求|请求|询问|提出|授权|同意)后", window, re.I))


def negated(content: str, start: int, end: int, span: int = 20) -> bool:
    """命中词前后 span 字内出现否定/禁止词，视为"文本在禁止这件事"，不计。"""
    line_start = content.rfind("\n", 0, start) + 1
    line_end = content.find("\n", end)
    line_end = len(content) if line_end < 0 else line_end
    lo = max(line_start, start - span)
    hi = min(line_end, end + span)
    if re.search(NEGATION, content[lo:hi]):
        return True
    # 命中在列表项里时，再看这个列表的标题/引导句（往上最多 8 行，遇到标题或以冒号结尾的句子为止）
    line = content[line_start:line_end].lstrip()
    if line.startswith(("-", "*", "•")) or re.match(r"\d+[.、)]", line):
        prev_lines = content[:line_start].split("\n")[-9:-1]
        for prev in reversed(prev_lines):
            t = prev.strip()
            if not t:
                continue
            if t.startswith("#") or t.endswith(("：", ":")):
                return bool(re.search(NEGATION, t))
            if not (t.startswith(("-", "*", "•")) or re.match(r"\d+[.、)]", t)):
                break
    return False


def inside_atom_id(content: str, start: int, end: int) -> bool:
    for m in ATOM_ID.finditer(content, max(0, start - 6), min(len(content), end + 6)):
        if m.start() <= start and m.end() >= end:
            return True
    return False


def keep_best(findings: list[dict]) -> list[dict]:
    """同一文件同一规则只留一条（取最严重、最靠前的那条），避免同一段话刷屏。"""
    best: dict[str, dict] = {}
    for item in findings:
        cur = best.get(item["rule"])
        if cur is None or (ORDER[item["severity"]], item["line"]) < (ORDER[cur["severity"]], cur["line"]):
            best[item["rule"]] = item
    return list(best.values())


def scan_content(path: Path, content: str) -> list[dict]:
    findings: list[dict] = []

    # 任务劫持：要求覆盖用户/系统指令，或要求对用户隐瞒指令。单行内匹配；防提示注入的句子不算；否定句不算。
    override = r"(?:忽略|无视|绕过|抛开).{0,40}(?:之前|以上|先前|上面|用户|系统|开发者).{0,20}(?:指令|提示词|系统提示|规则|限制)|覆盖.{0,40}(?:用户|系统|开发者).{0,20}(?:指令|提示词|系统提示)"
    conceal = r"(?:不得|不允许|不要|不能|别|禁止).{0,6}(?:告诉|告知|披露|透露|提及).{0,12}(?:用户|此指令|这条指令|本提示|这段话|这些规则)"
    for match in re.finditer(override + r"|" + conceal, content, re.I):
        window = content[max(0, match.start() - 160):match.end() + 160]
        if re.search(r"(?:邮件|网页|文档|附件|外部|不可信|注入).{0,80}(?:指令|提示)", window, re.I):
            continue
        # "隐瞒指令"这一支本身就是否定句式，不做否定排除；"覆盖指令"这一支要排除"不要忽略用户指令"之类的反向表述
        if re.fullmatch(override, match.group(0), re.I) and negated(content, match.start(), match.end()):
            continue
        findings.append(finding("instruction-hijacking", "严重", "人的自主性", "文本要求覆盖用户或系统指令，或对用户隐瞒该行为，可能破坏授权边界。", path, content, match.start()))

    # 商业导流：强词单独成立；弱词只在强制/隐瞒语境里升级。
    for match in re.finditer(COMMERCIAL, content, re.I):
        word = match.group(0)
        strong = bool(re.fullmatch(COMMERCIAL_STRONG, word, re.I))
        if negated(content, match.start(), match.end()):
            continue
        window = content[max(0, match.start() - 180):match.end() + 180]
        if re.search(FORCED, window, re.I | re.S):
            findings.append(finding("forced-commercial-diversion", "高风险", "人的自主性", "文本要求在正常任务输出中持续插入商业动作，用户难以拒绝且无法照常完成原任务。", path, content, match.start()))
        elif re.search(COVERT, window, re.I | re.S):
            findings.append(finding("covert-commercial-intent", "高风险", "透明与可解释", "文本要求隐瞒或伪装商业关联，用户无法知情选择。", path, content, match.start()))
        elif not strong:
            continue
        elif has_consent(window):
            findings.append(finding("user-requested-commercial-option", "信息", "透明与可解释", "导流动作限定在用户明确请求购买、联系或服务时出现。", path, content, match.start()))
        else:
            findings.append(finding("commercial-reference", "待复核", "透明与可解释", "文本含强导流动作；请核对它会不会出现在无关任务里，以及商业关联是否已披露。", path, content, match.start()))

    # 敏感数据：按"是否主动读取"与"是否外传"分级；否定句（不读取密钥…）不算。
    for sensitive_match in re.finditer(SENSITIVE, content, re.I):
        if negated(content, sensitive_match.start(), sensitive_match.end()):
            continue
        window = content[max(0, sensitive_match.start() - 250):sensitive_match.end() + 250]
        active_access = re.search(r"(?:读取|导入|获取|访问|提取|复制|收集).{0,80}" + SENSITIVE + r"|" + SENSITIVE + r".{0,80}(?:读取|导入|获取|访问|提取|复制|收集)", window, re.I | re.S)
        exfiltration = re.search(SENSITIVE + r".{0,240}" + NETWORK + r"|" + NETWORK + r".{0,240}" + SENSITIVE, window, re.I | re.S)
        if active_access and exfiltration:
            findings.append(finding("sensitive-data-exfiltration", "严重", "安全与可靠", "文本同时涉及读取敏感数据与向外部发送/上传；立即核对数据去向和授权。", path, content, sensitive_match.start()))
        elif active_access and has_consent(window):
            findings.append(finding("authorized-sensitive-access", "信息", "透明与可解释", "敏感数据操作写明了用户明确授权的前提；执行前仍应展示范围与去向。", path, content, sensitive_match.start()))
        elif active_access:
            findings.append(finding("undisclosed-sensitive-access", "高风险", "安全与可靠", "文本涉及读取或导入敏感数据，但没有看到用户授权前提。", path, content, sensitive_match.start()))

    # 外部命令：只认小写命令形态；原子 id（SCP-013）不算；有敏感词+网络词共现的已在上面判过。
    for match in re.finditer(r"\b(?:curl|wget|nc|ncat|ssh|scp)\b", content):
        if inside_atom_id(content, match.start(), match.end()):
            continue
        if re.search(r"(?:敏感|cookie|凭据|密钥|token).{0,240}" + NETWORK, content, re.I | re.S):
            break
        findings.append(finding("external-command", "待复核", "安全与可靠", "文本包含外部命令或网络访问；核对目标、数据范围和用户授权。", path, content, match.start()))
        break
    return keep_best(findings)


def scan_skill(skill_dir: Path) -> dict:
    findings: list[dict] = []
    for file_path in scanned_files(skill_dir):
        try:
            findings.extend(scan_content(file_path, file_path.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    findings.sort(key=lambda item: (ORDER[item["severity"]], item["file"], item["line"]))
    return {"name": skill_dir.name, "path": str(skill_dir), "is_symlink": skill_dir.is_symlink(), "findings": findings}


def print_report(results: list[dict], roots: list[Path], duplicates: int) -> None:
    counts = Counter(item["severity"] for result in results for item in result["findings"])
    print("# 本地 skill 审查报告")
    print(f"扫描范围：{', '.join(str(root) for root in roots if root.exists()) or '未找到默认目录'}")
    print(f"发现 skill：{len(results)}（已合并 {duplicates} 个软链、镜像或内嵌副本）")
    print(f"严重：{counts['严重']}｜高风险：{counts['高风险']}｜待复核：{counts['待复核']}｜信息：{counts['信息']}")
    for result in results:
        if not result["findings"]:
            continue
        print(f"\n## {result['name']}\n位置：`{result['path']}`")
        for item in result["findings"]:
            print(f"\n- {item['severity']}｜{item['rule']}｜{item['principle']}\n  - {item['file']}:{item['line']}\n  - {item['message']}\n  - 命中：`{item['excerpt']}`")
    if not any(result["findings"] for result in results):
        print("\n未发现本规则集中的风险信号。该结果不等于安全保证。")
    print("\n扫描未修改任何文件。隔离前请逐个确认目标路径。")


def command_scan(args: argparse.Namespace) -> int:
    roots = [Path(path).expanduser() for path in args.root] if args.root else DEFAULT_ROOTS
    skills, duplicates = find_skills(roots)
    skills = [path for path in skills if path.name != SELF_NAME]
    results = [scan_skill(path) for path in skills]
    if args.format == "json":
        print(json.dumps({"roots": [str(root) for root in roots], "deduplicated": duplicates, "skills": results}, ensure_ascii=False, indent=2))
    else:
        print_report(results, roots, duplicates)
    return 0


def command_quarantine(args: argparse.Namespace) -> int:
    skill_dir = Path(args.skill).expanduser().absolute()
    if not args.yes:
        print("拒绝执行：隔离操作需要 --yes。", file=sys.stderr); return 2
    if not (skill_dir / "SKILL.md").is_file() or skill_dir.name == SELF_NAME:
        print(f"拒绝执行：目标必须是 {SELF_NAME} 以外的 skill 目录（含 SKILL.md）。", file=sys.stderr); return 2
    if skill_dir.is_symlink():
        target = os.readlink(skill_dir); skill_dir.unlink()
        print(json.dumps({"action": "removed_symlink", "path": str(skill_dir), "source_retained": target, "reason": args.reason}, ensure_ascii=False)); return 0
    destination = QUARANTINE_ROOT / datetime.now().strftime("%Y%m%d-%H%M%S") / skill_dir.name
    destination.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(skill_dir), str(destination))
    print(json.dumps({"action": "quarantined", "from": str(skill_dir), "to": str(destination), "reason": args.reason}, ensure_ascii=False)); return 0


def command_list_quarantine(_: argparse.Namespace) -> int:
    entries = sorted(QUARANTINE_ROOT.rglob("SKILL.md")) if QUARANTINE_ROOT.exists() else []
    print("\n".join(str(item.parent) for item in entries) or "隔离区为空。")
    return 0


def command_restore(args: argparse.Namespace) -> int:
    source, target = Path(args.source).expanduser().absolute(), Path(args.target).expanduser().absolute()
    if not args.yes or not str(source).startswith(str(QUARANTINE_ROOT)) or not (source / "SKILL.md").is_file() or target.exists() or target.is_symlink():
        print("拒绝执行：需使用 --yes；来源须在隔离区且目标不存在。", file=sys.stderr); return 2
    target.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(source), str(target))
    print(json.dumps({"action": "restored", "from": str(source), "to": str(target)}, ensure_ascii=False)); return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描与隔离本地 skill。")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan", help="只读扫描 skill"); scan.add_argument("--root", action="append", default=[]); scan.add_argument("--format", choices=["text", "json"], default="text"); scan.set_defaults(handler=command_scan)
    quarantine = subparsers.add_parser("quarantine", help="隔离一个明确指定的 skill"); quarantine.add_argument("skill"); quarantine.add_argument("--reason", default="用户确认"); quarantine.add_argument("--yes", action="store_true"); quarantine.set_defaults(handler=command_quarantine)
    listing = subparsers.add_parser("list-quarantine", help="列出隔离区"); listing.set_defaults(handler=command_list_quarantine)
    restore = subparsers.add_parser("restore", help="从隔离区恢复 skill"); restore.add_argument("source"); restore.add_argument("target"); restore.add_argument("--yes", action="store_true"); restore.set_defaults(handler=command_restore)
    args = parser.parse_args(); return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
