#!/usr/bin/env python3
"""xy-atomize 批次验收器：检查一卷待入库的原子 jsonl 能不能进 knowledge/_internal/incoming/。

用法：
  python3 skills/xy-atomize/scripts/validate_batch.py <batch.jsonl> [--atoms knowledge/atoms.jsonl] [--dup 0.80] [--names tools/name_blocklist.txt]

检查项（任一 ✗ 即退出码 1）：
  1. 每行是合法 JSON，且是对象
  2. 必填字段：id / type / knowledge / confidence / topics / source_type / source_label
  3. id 形如 XY-U<2~3 位大写>-<3 位数字>，同卷不重复，且不与主库撞
  4. source_type 必须是 user_import
  5. type ∈ {definition, principle, method, case, anti-pattern, insight, number}；confidence ∈ {high, medium}
  6. topics 非空且都在 13 个主题内
  7. knowledge 20–320 字；original（可选）≤ 200 字
  8. 疑似真名：命中黑名单，或"X 老师 / X 总 / X 哥 / X 姐 / @xxx"形态 → 报出来人工看
  9. 与主库近重复：knowledge 与任一已有原子相似度 ≥ --dup（默认 0.80）→ 报出来人工决定去留
只读，不改任何文件。
"""
import sys, os, re, json, difflib, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
TOPICS = ["私域运营", "流量获取", "选品逻辑", "IP人设", "团队与模式设计", "认知与心态", "内容创作与平台", "商业案例与实战复盘", "合规与风控", "新人起步方法论", "成交与话术", "AI与工具", "中国市场与下沉"]
TYPES = {"definition", "principle", "method", "case", "anti-pattern", "insight", "number"}
CONF = {"high", "medium"}
ID_RE = re.compile(r"^XY-U[A-Z]{2,3}-\d{3}$")
NAME_RE = re.compile(r"[一-龥]{1,2}(?:老师|总|哥|姐|董|校长)|@[\w一-龥]{2,}")
REQUIRED = ["id", "type", "knowledge", "confidence", "topics", "source_type", "source_label"]


def load_atoms(path):
    rows = []
    if os.path.exists(path):
        for l in open(path, encoding="utf-8"):
            if l.strip():
                try:
                    rows.append(json.loads(l))
                except Exception:
                    pass
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch")
    ap.add_argument("--atoms", default=os.path.join(ROOT, "knowledge", "atoms.jsonl"))
    ap.add_argument("--dup", type=float, default=0.80)
    ap.add_argument("--names", default=os.path.join(ROOT, "tools", "name_blocklist.txt"))
    a = ap.parse_args()

    atoms = load_atoms(a.atoms)
    ids = {r["id"] for r in atoms if "id" in r}
    knows = [(r["id"], r.get("knowledge", "")) for r in atoms]
    names = []
    if os.path.exists(a.names):
        names = [l.strip() for l in open(a.names, encoding="utf-8") if l.strip() and not l.startswith("#")]

    errors, warns, seen = [], [], set()
    rows = []
    for n, line in enumerate(open(a.batch, encoding="utf-8"), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            assert isinstance(r, dict)
        except Exception:
            errors.append(f"L{n} 不是合法 JSON 对象"); continue
        rows.append((n, r))
        miss = [k for k in REQUIRED if k not in r]
        if miss:
            errors.append(f"L{n} 缺字段 {miss}"); continue
        i = r["id"]
        if not ID_RE.match(i): errors.append(f"L{n} id 形态不对：{i}（应为 XY-U<2~3位大写>-<3位数字>）")
        if i in seen: errors.append(f"L{n} 同卷重复 id：{i}")
        if i in ids: errors.append(f"L{n} 与主库撞 id：{i}")
        seen.add(i)
        if r["source_type"] != "user_import": errors.append(f"L{n} source_type 应为 user_import：{r['source_type']}")
        if r["type"] not in TYPES: errors.append(f"L{n} type 不合法：{r['type']}")
        if r["confidence"] not in CONF: errors.append(f"L{n} confidence 不合法：{r['confidence']}")
        tp = r["topics"]
        if not isinstance(tp, list) or not tp: errors.append(f"L{n} topics 为空")
        else:
            bad = [t for t in tp if t not in TOPICS]
            if bad: errors.append(f"L{n} topics 不在清单内：{bad}")
        k = r["knowledge"] or ""
        if not (20 <= len(k) <= 320): errors.append(f"L{n} knowledge 长度 {len(k)}（要求 20–320 字）")
        o = r.get("original")
        if o and len(o) > 200: errors.append(f"L{n} original 超 200 字（{len(o)}）")
        text = k + " " + (o or "")
        for nm in names:
            if nm and nm in text: errors.append(f"L{n} 命中真名黑名单：{nm}")
        m = NAME_RE.search(text)
        if m: warns.append(f"L{n} 疑似人名/账号称呼「{m.group(0)}」，人工看一眼：{k[:40]}…")
        # 近重复
        best, best_id = 0.0, None
        for aid, ak in knows:
            if abs(len(ak) - len(k)) > 80: continue
            sm = difflib.SequenceMatcher(None, ak, k)
            if sm.quick_ratio() < a.dup: continue
            s = sm.ratio()
            if s > best: best, best_id = s, aid
        if best >= a.dup: warns.append(f"L{n} 与 {best_id} 相似 {best:.2f}，疑似重复：{k[:40]}…")

    # 同卷内近重复
    for x in range(len(rows)):
        for y in range(x + 1, len(rows)):
            kx, ky = rows[x][1].get("knowledge", ""), rows[y][1].get("knowledge", "")
            if kx and ky and abs(len(kx) - len(ky)) <= 80 and difflib.SequenceMatcher(None, kx, ky).ratio() >= a.dup:
                warns.append(f"L{rows[x][0]} 与 L{rows[y][0]} 同卷近重复")

    print(f"# 批次验收：{a.batch}")
    print(f"条数 {len(rows)}｜✗ 硬错误 {len(errors)}｜⚠ 待人工 {len(warns)}")
    for e in errors: print("✗", e)
    for w in warns: print("⚠", w)
    if not errors:
        print("✓ 结构合法、无重复 id、无黑名单真名；⚠ 项人工过一遍后即可放入 knowledge/_internal/incoming/ 并运行 python3 tools/build_atoms.py")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
