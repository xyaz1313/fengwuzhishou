#!/usr/bin/env python3
"""校验正式 skill 是否遵守 _shared/routing-contract.md 里的规则。

硬性校验(不过直接 fail，退出码 1)：
1. 每个叶子 skill(除 xy、xy-coach)必须含统一收尾句核心措辞"不替用户预设下一站"。
2. 叶子 skill 不能出现硬编码指定下一站的措辞(路由到/转到/交给/建议…用/建议先去/试试 + /xy-xxx)。

软性校验(不 fail，只列出人工复核清单)：
3. skill 里出现"Phase 2"/"## 阶段 2"式多小节结构、但没有★停顿标记的，列出来人工确认是否走了
   routing-contract.md 允许的"写法 C"（结构改写版，需在 skill 内说明为什么不能用写法 A）。
"""

import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT_DIR / "skills"

HUB_SKILLS = {"xy", "xy-coach"}

CLOSING_SENTENCE_MARKER = "不替用户预设下一站"

HARDCODED_HANDOFF_PATTERNS = (
    re.compile(r"(?:路由到|转到|交给)\s*[`*]*(/?xy-[a-z0-9-]+)"),
    re.compile(r"建议(?:你)?(?:先)?(?:用|去)\s*[`*]*(/?xy-[a-z0-9-]+)"),
    re.compile(r"试试\s*[`*]*(/?xy-[a-z0-9-]+)"),
)

PHASE2_MARKER = re.compile(r"Phase\s*2\b|##\s*阶段\s*2")
PAUSE_MARKER = "★ 停顿"


def main() -> None:
    errors: list[str] = []
    warnings: list[str] = []

    skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())
    leaf_count = 0

    for skill_dir in skill_dirs:
        name = skill_dir.name
        skill_path = skill_dir / "SKILL.md"
        if not skill_path.is_file():
            errors.append(f"缺少定义文件：skills/{name}/SKILL.md")
            continue
        if name in HUB_SKILLS:
            continue

        leaf_count += 1
        text = skill_path.read_text(encoding="utf-8")

        # 1. 统一收尾句
        if CLOSING_SENTENCE_MARKER not in text:
            errors.append(f"skills/{name}/SKILL.md 缺少统一收尾句核心措辞「{CLOSING_SENTENCE_MARKER}」")

        # 2. 硬编码交接措辞禁令
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern in HARDCODED_HANDOFF_PATTERNS:
                match = pattern.search(line)
                if match:
                    errors.append(
                        f"skills/{name}/SKILL.md:{line_number} "
                        f"疑似硬编码指定下一站 {match.group(1)}：{line.strip()}"
                    )
                    break

        # 3. Phase 2 多小节 + 无★停顿标记 -> 人工复核清单（软性）
        if PHASE2_MARKER.search(text) and PAUSE_MARKER not in text:
            warnings.append(
                f"skills/{name}/SKILL.md 含 Phase 2 式结构但无「{PAUSE_MARKER}」标记，"
                f"需人工确认是否合规使用了写法 C（结构改写版）"
            )

    if warnings:
        print("以下 skill 需人工复核（不算失败，仅提醒）：", file=sys.stderr)
        for w in warnings:
            print(f"- {w}", file=sys.stderr)
        print(file=sys.stderr)

    if errors:
        print("路由契约校验失败：", file=sys.stderr)
        for e in errors:
            print(f"- {e}", file=sys.stderr)
        sys.exit(1)

    print(f"路由契约校验通过：{leaf_count} 个叶子 skill 全部符合统一收尾句与措辞禁令。")
    if warnings:
        print(f"另有 {len(warnings)} 项需人工复核，见上方列表。")


if __name__ == "__main__":
    main()
