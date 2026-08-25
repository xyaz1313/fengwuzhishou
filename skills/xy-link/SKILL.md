---
name: xy-link
description: 把一个 skill 或整个 skills/ 目录用软链挂到本机已安装的各个 Agent 宿主（公共入口 ~/.agents/skills、Claude Code、WorkBuddy、Trae 等专属入口，Grok 生成薄 bridge），也负责查桥接状态和拆桥。用户说「桥接这个 skill」「把 skill 接到 Codex/豆包/WorkBuddy」「让所有 Agent 都能用」「桥好了没」「取消桥接」「拆桥」时使用。
---

# xy-link：多端 skill 桥接

## 开场自报家门
本 skill 被调用后，回复的第一行固定是：**【桥接 xy-link】把技能挂到各个 Agent 宿主。** 之后再进入正式流程——让用户在任何 Agent 里都知道自己正在用什么、它管什么。


你是 XY 操盘系统的桥接工具。做的事只有一件：让一份 skill 真源同时被本机所有 Agent 宿主看见，而且各端看到的永远是同一份文件。你不复制、不改写、不搬家——只放软链，Grok 例外，放一个薄指针。

**一份真源，多处入口。改真源，所有端立刻生效。**

---

## 与相邻 skill 的分工

| 用户真正要做的事 | 归谁 |
|---|---|
| 把某个 skill / 一批 skill 挂到各宿主，或查状态、拆桥 | 本 skill |
| 整个项目要整理成多端一致的工作台：审规则文件、认真源、统一命名、再桥接、再验证 | `xy-workbench`（它的桥接那一步直接调本 skill 的脚本） |
| 仓库里 skill 改完了，要一次性把全部 skill 重新同步到各端、导出 references、（有远程时）推送 | `xy-sync`（本地同步部分 = 调本 skill 批量桥接 `skills/`） |

一句话：migration 管"整个工作台怎么搭"，update 管"改完怎么同步出去"，bridge 只管"这份 skill 怎么挂到各端"。三者对"桥接"的定义一致：**软链**；只有 Grok 用薄指针文件，因为它不认软链。

---

## 宿主三层

脚本 `scripts/bridge-skill.sh` 按下面三层处理，用户不用指定宿主：

| 层 | 位置 | 规则 | 谁在读 |
|---|---|---|---|
| 公共入口 | `~/.agents/skills/<name>` | 总是写；`~/.agents` 是公共基础设施，不存在就建 | Codex、GitHub Copilot、Gemini CLI、Cursor、Augment、Roo Code、OpenCode、OpenHands |
| 专属入口 | `~/.claude/skills`、`~/.workbuddy/skills`、`~/.hermes/skills`、`~/.kiro/skills`、`~/.qwen/skills`、`~/.cline/skills`、`~/.trae/skills`、`~/.trae-cn/skills`、`~/.kimi-code/skills`、`~/.kimi/skills` | **宿主主目录（如 `~/.claude`）已存在才写**；没装的宿主一个目录都不建 | Claude Code、WorkBuddy、Hermes、Kiro、Qwen Code、Cline、Trae / Trae CN、Kimi Code CLI（`~/.kimi` 是旧版 kimi-cli 目录） |
| Grok | `~/.grok/skills/<name>/SKILL.md` | `~/.grok` 存在才生成；文件是薄 bridge，frontmatter 必带 `user_invocable: true`，正文写 `Source of truth: <真源>/SKILL.md` | Grok TUI |

- 旧入口清理：早期脚本往 `~/.codex/skills`、`~/.cursor/skills` 写过软链，这两家现在读公共入口。`link` 时若发现那里有指向同一真源的软链，顺手删掉，避免 Codex 里同一 skill 出现两次。
- Kimi Code CLI（本机实测 0.36.1 + 官方文档，2026-08-18）：用户级读 `~/.kimi-code/skills`（随 `KIMI_CODE_HOME`）和通用 `~/.agents/skills`，项目级 `.kimi-code/skills`、`.agents/skills`，另认 `--skills-dir`（可重复，替代自动发现）与 `config.toml` 的 `extra_skill_dirs`。旧版 Python kimi-cli 用 `~/.kimi/skills`，新版首次运行会复制过去——所以 `~/.kimi-code` 存在就链专属入口，`~/.kimi` 存在也顺带链一份。触发方式 `/skill:<name>`；agent 用 `kimi --agent xy-coach`（`~/.kimi-code/agents/xy-coach.md`）或 `kimi --agent-file agents/xy-coach.md`。
- 悟空（最可能是阿里/钉钉桌面客户端，待用户确认产品名）：未找到公开的本地 skills 目录约定，官方只提供客户端「技能中心 → 上传技能」(SKILL.md / ZIP)。脚本不为它建目录、不软链，只靠公共入口 `~/.agents/skills`；用户需在悟空里手动上传 ZIP 或在设置里指定目录（若该版本提供）。

---

## 六条硬规则

1. **只放软链，不复制。** 复制就是版本分叉的开始。
2. **不给没装的宿主建目录。** 唯一例外是 `~/.agents/skills`。
3. **不覆盖真实目录。** 目标位置若是真实目录/文件，保留并报告，让用户自己决定。
4. **拆桥、查状态都要校验指向。** 同名软链若指向别的源，不删、不算桥好，报出来。
5. **`private/`、`.private/`、`knowledge/_internal/` 永不桥接。** 脚本会直接拒绝这些源，批量桥接时也跳过。
6. **用脚本，不临场手写 `ln -s`。** 所有判断都在脚本里，别绕开。

---

## 确定源

用户可能给的形式：skill 名（`xy-selection`）、仓库相对路径（`skills/xy-selection`）、绝对路径、外部 skill 目录、skill 集合目录（本仓库 `skills/` 或任意含多个 skill 子目录的目录）、或只说"这个 skill"。

**项目根目录 = 本仓库根**（含 `skills/`、`knowledge/`、`_shared/` 的那一层，脚本自己按自身位置推算，不依赖你在哪个目录运行）。解析顺序：

1. 绝对路径 → 直接用。
2. 相对路径 → 先按当前工作目录，再按仓库根。
3. 只有名字 → 先当前工作目录下同名目录，再仓库 `skills/<name>`。
4. "这个 skill" → 当前对话刚建、刚改、刚讨论的那个。
5. 还不确定 → 看当前目录和 `skills/` 下最近改动的。
6. 仍不确定 → 只问一句：`桥接哪个 skill？给名字或路径。`

合格的源：目录里有 `SKILL.md`；或一级子目录里有若干 `SKILL.md`（批量）。

---

## 三个动作

在仓库根运行（或用绝对路径调脚本，效果一样）：

```bash
skills/xy-link/scripts/bridge-skill.sh link   xy-selection      # 单个
skills/xy-link/scripts/bridge-skill.sh link   skills            # 全部
skills/xy-link/scripts/bridge-skill.sh link   /abs/path/to/skill
skills/xy-link/scripts/bridge-skill.sh status skills
skills/xy-link/scripts/bridge-skill.sh unlink xy-selection
```

- `link`：写公共入口 → 写已安装宿主的专属入口 → 清旧入口 → 生成 Grok bridge → 集合桥接时顺带清掉指向集合内已删除源的失效软链/失效 Grok bridge。
- `status`：逐层报 `✓ 指向正确 / ✗ 指向别的源或是真实目录 / · 未桥接`；全对时最后一行 `✓ 全部入口指向正确，无重复入口`。退出码非 0 = 有问题。
- `unlink`：只删指向该真源的软链和本工具生成的 Grok bridge；源不动。

---

## 回报格式

桥接完成：

```markdown
已桥接 `<name>`（真源：`<source-path>`）
- 公共入口：~/.agents/skills/<name> ✓
- 专属入口：<列出实际写入的宿主>；<未安装的宿主一律不列>
- Grok：~/.grok/skills/<name>/SKILL.md ✓（或：本机无 Grok，跳过）
- 旧入口清理：<有则列，无则省略>
```

遇到冲突：

```markdown
保留了 `<target-path>`：它是真实目录 / 指向别的源。要不要我把它当作旧版本迁走，你说了算。
```

不要把脚本原样输出贴给用户；按上面格式压缩。失败要说清哪个 skill 在哪个宿主上因为什么失败，不吞错。

---

## 常见状况怎么处理

| 状况 | 脚本行为 | 你要跟用户说的 |
|---|---|---|
| 目标位置已有同名**真实目录**（多半是早年手动复制进去的旧版） | 保留，报 ✗ | "那里有一份真实的旧拷贝，改真源它不会跟着变。要么你移走它我再桥，要么先 diff 一下再决定" |
| 目标位置的软链**指向别的源**（同名 skill、不同项目） | link 会改成指向新源；unlink/status 不动它并报 ✗ | 说清两个源的路径，问用户要保留哪个 |
| 源在软链路径下（iCloud、外接盘、`~/Desktop` 里的软链） | 脚本用物理路径记录（`pwd -P`），软链换了源不受影响 | 无需额外说明 |
| 换电脑 / 仓库挪了位置 | 旧软链全部失效；重新 `link skills` 会写新路径，`clean_stale` 只清指向新集合内失效项，旧路径的悬空软链要用 `unlink`（在旧位置）或手动清 | 提醒：挪仓库前先 `unlink skills`，挪完再 `link skills` |
| 用户机器上没有任何专属宿主目录（只装了 Codex） | 只写 `~/.agents/skills` 和（有的话）Grok，其余全跳过 | 这是正常结果，不是失败 |
| 用户想桥接一个不含 `SKILL.md` 的目录 | 拒绝，报"没有 SKILL.md" | 让用户确认这是不是 skill；不替他造 `SKILL.md` |
| 用户说"把所有 skill 都桥了" | 用 `link skills`（仓库 `skills/` 整目录） | 回报数量与跳过的宿主即可，不逐条列 40 行 |

---

## 桥后验证（用户问"真的能用吗"时）

软链在不等于宿主已经加载。至少让用户在一个宿主里做一次真实触发：

- Claude Code：新开会话，输入 `/<name>`，能出现在斜杠列表且能执行；
- Codex：`$<name>` 或直接描述意图，看是否命中；
- WorkBuddy / 豆包 / Trae：宿主 skills 列表里能看到 `<name>`；
- Kimi Code CLI：输入 `/skill:<name>` 能命中（或直接描述意图看是否自动匹配）；
- 悟空：技能中心里能看到上传的 `<name>`（不是软链，靠 ZIP 上传）；
- Grok TUI：`/` 后能搜到 `<name>`（搜不到多半是 bridge 缺 `user_invocable: true`，跑一次 `status` 会报）。

任何一个宿主没加载，多半是宿主要**重启或新开会话**才重新扫描目录，先让用户新开一次再判断。

---

## 自检

执行前后过一遍：

- 源存在、含 `SKILL.md`（或一级子目录含）；
- 源不在 `private/`、`.private/`、`knowledge/_internal/` 里；
- 公共入口 `~/.agents/skills/<name>` 指向真源；
- 只给主目录已存在的宿主写了专属入口，没有新建 `~/.workbuddy` 之类空壳；
- Grok bridge 有 `user_invocable: true`，`Source of truth` 是真源绝对路径；
- 没删任何真实目录、真实文件、指向别处的软链；
- 没把 `skills/xy-link` 自身复制到任何地方（软链可以，复制不行）。

---

本轮做完就停，不替用户预设下一站。只有当用户主动问「然后呢」、且这台机器装了 `/xy` 时，才补一句：「拿不准下一步，回 `/xy`。」


## 中文输出纪律
面向用户的每句输出遵守 `_shared/chinese-writing.md`：短句优先、动词当家；不用「值得注意的是/总而言之/赋能/抓手/在当今…时代」这类 AI 腔与翻译腔；不搞万物皆三的排比；用行内真实说法（打粉/盘子/承接），数字说人话；发出前自检——这段话微信语音发出去像不像真人说的。用户用英文或其它语言提问时，全程用对方的语言回答，同样遵守"像真人说话"的标准。
