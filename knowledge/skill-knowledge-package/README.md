# XY 知识包说明

如果你不想装 skill，只想直接拿 XY 操盘系统的判断方法论用——贴到自己的 AI 提示词里、做 RAG、或者当文档读——这个文件夹就是给你的。

## 这里有什么

6 份文档，按主题打包了 XY 43 个正式 skill 里、24 个判断/诊断类 skill 的"核心哲学/信条"部分，原样从 SKILL.md 正文抽出来，脱离 skill 的执行流程（Phase、追问节奏、停顿规则）：

| 文件 | 覆盖 skill | 信条数 |
| --- | --- | --- |
| `biz-diagnosis_公理与方法论.md` | xy-biz-scan / xy-selection / xy-mode / xy-ops | 23 |
| `private-ops-close_公理与方法论.md` | xy-close / xy-private-ops / xy-newbie / xy-traffic | 29 |
| `ip-expression_公理与方法论.md` | xy-ip / xy-echo-test / xy-human-touch | 17 |
| `content-creation_公理与方法论.md` | xy-content-scan / xy-opener / xy-script-glue / xy-idea-desk / xy-clip / xy-replica | 24 |
| `execution-psychology_公理与方法论.md` | xy-kickoff / xy-slow-lane / xy-goal-card / xy-question-spec | 13 |
| `concept-precedent_公理与方法论.md` | xy-term-crack / xy-precedent / xy-peer-pick | 9 |

工具类/工程类 skill（xy-link、xy-sync、xy-vault、xy-workbench、xy-archive、xy-resume、xy-brief、xy-casefile、xy-skill-audit、xy-course、xy-roundtable、xy-coach、xy、xy-publish-guard、xy-atomize、xy-mp-layout、xy-xhs-headline）不带判断类"信条"，本次未纳入打包。`xy-xhs-headline` 是 75 个可直接套用的小红书标题公式模板库，性质和这份"判断方法论"打包不同，需要的话另见 `skills/xy-xhs-headline/`。

## 怎么用

- 直接当文档读，了解 XY 系统怎么判断私域/短视频/商业问题。
- 拿去粘自己的 AI 提示词。
- 拿 `../atoms.jsonl` 做 RAG——每份文档句末括号里的编号（如"参考 XY-DY-006"）对应 `atoms.jsonl` 里的原子 id，可以按 id 查到完整原子记录（含原文出处、置信度、来源类型等字段）。

## 来源与真实性

原子来源不单一：一部分是账号/课程/自身实战一手内容（`source_type: course / user_import / account_video`），一部分是书籍蒸馏（`book_distilled`），一部分是第三方商业咨询方法论经重写、脱敏后的内化内容（`third_party_ip`，正文不点名具体第三方来源）——`atoms.jsonl` 里每条原子的 `source_type` 字段标了具体来源类型，不隐藏这个区分。

## 许可证

CC BY-NC 4.0，同仓库。个人使用不需要署名，公开发布注明来源，商用需要单独授权，联系方式见仓库根目录 README。
