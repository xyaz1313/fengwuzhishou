# Fengwu Zhishou · XY Business Operating System

[中文](README.md) | **English**

![Fengwu Zhishou](docs/assets/banner.png)

> *Seen every playbook, kept to first principles.*

**A business & private-domain consultant that lives inside your AI.** Built by a Chinese private-domain operator with 20 years of hands-on experience — scaling a TCM wellness brand to ¥125M in 10 months, an aromatherapy brand to ¥240M in 2 years — this system packages that judgment into **45 Skills** backed by **27,853 knowledge atoms**. Every judgment traces back to a specific atom ID; when it genuinely can't find one, it says so instead of making one up.

One premise up front: **your private domain can generate its own traffic.** Don't buy into the "grow traffic first, build private domain later" split — your WeChat moments are already an ad slot, your repeat customers already refer new ones, content and lead-gen are capabilities private domain owns on its own.

[Get started](#get-started) · [What it solves](#what-it-solves) · [What's inside](#whats-inside) · [Install](#install)

## Get started

Say this in your Agent once it's installed:

```text
/xy A customer added me on WeChat, chatted a bit, said "too expensive," and went quiet.
Not sure if I should drop the price, change my pitch, or if they were never my target customer.
```

Already know what you want? Name the skill directly (every skill introduces itself in its first line):

```text
/xy-close A customer thinks it's too expensive and stopped replying — is this deal still savable?
/xy-mode I'm designing a three-tier commission structure — check if it crosses any lines.
/xy-selection A supplier friend wants me to sell his enzyme product — is this a good pick?
/xy-vault Turn this folder into my business knowledge base so I can query it directly.
```

Not sure where to start? Say `/xy-coach` — chat with **Xiaoye** (the author's AI persona) for a few minutes like you're talking to a friend, and your business profile gets built (saved locally to `~/.xy/`). Every judgment after that is grounded in your actual numbers.

## What it solves

You don't need to learn a framework or know which tool to call. Hand `/xy` whatever you're stuck on, and it reads where your business actually is; every round closes with three lines: **the one next action, the number to watch, the evidence behind it.**

| Where you're stuck | What you get |
| --- | --- |
| Can't tell if the business is even worth continuing | Seven-point health check, from net profit to growth stage, every call cited |
| Not sure if a product is worth carrying | Two-axis classification, full-cost accounting, three-round paid-test method |
| Customer thinks it's too expensive and goes quiet | Full diagnostic across the whole closing chain, from first chat to repeat purchase |
| Paid ads keep losing money — stop or push through? | Whether to run paid traffic at all, folded into a basic-viability check |
| New account has no traffic, afraid to get banned for lead-gen | Account-warmup and lead-gen path design, tactics ranked by risk |
| Don't know what to post, old customers have gone quiet | Content mix, tagging, concrete reactivation moves |
| Not sure the commission structure is legal | Five-dimension structural review, compliance research paths (no legal verdicts) |
| Can't keep the team, don't know how to set commissions | Efficiency red lines, payout structure, launch-pace review |
| Want a few different perspectives on one decision | Roundtable: 3–5 frameworks argue it out and a verdict gets called |
| Want to pick up last session's conclusion | Local archive: save, resume, case-file backfill — all on your own machine |

## How routing and memory connect

![XY single-step routing](docs/assets/routing-flow.png)

One skill at a time. Each round's conclusion becomes the input for the next round's routing — nothing pre-chains into a default sequence:

![How the system connects](docs/assets/system-flow-readme.png)

## What's inside

45 skills across 13 areas — plain language routes you in automatically, or call a skill by name:

| Area | Call directly | What you typically get |
| --- | --- | --- |
| Business diagnosis & model | `/xy-biz-scan` `/xy-mode` `/xy-ops` | Seven-point health check, commission review, efficiency & launch-readiness calls |
| Enterprise AI consulting | `/xy-fde` | Off-the-shelf vs. custom calls, pricing models, org-adoption resistance |
| Product selection & supply chain | `/xy-selection` | Two-axis classification, cost accounting, paid-test plan |
| IP & positioning | `/xy-ip` `/xy-goal-card` | Seven positioning criteria, an executable goal card |
| Content creation | `/xy-content-scan` `/xy-opener` `/xy-script-glue` `/xy-human-touch` | Five-dimension diagnosis, opening-line candidates, flow check, de-AI-flavor pass |
| Titles & distribution | `/xy-xhs-headline` `/xy-echo-test` | Top-3 titles, resonance-mechanism breakdown |
| Traffic & lead-gen | `/xy-traffic` `/xy-peer-pick` | Account-warmup & lead-gen path, benchmark screening |
| Long-form editing | `/xy-clip` `/xy-recut` | Turn a transcript into short-video segments, or trim/reorder a long video |
| Private-domain ops & closing | `/xy-private-ops` `/xy-close` | Full diagnosis from WeChat moments to repeat purchase |
| Playbooks & precedent | `/xy-playbook` `/xy-precedent` | 8 industry playbook templates, historically-analogous cases |
| Publishing risk | `/xy-publish-guard` `/xy-skill-audit` | Pre-publish risk sweep, local skill security check |
| Frameworks & learning | `/xy-roundtable` `/xy-course` `/xy-term-crack` | Roundtable debate, interactive courses, concept breakdowns |
| Memory & workbench | `/xy-archive` `/xy-resume` `/xy-casefile` `/xy-vault` `/xy-workbench` | Local archives, decision case files, knowledge base, cross-host bridging |

Full skill list with Chinese names, trigger conditions, and sample inputs: [XY 指令清单](docs/XY指令清单.md) (Chinese only).

## Install

**Easiest:**

```bash
npx -y skills add xyaz1313/xyskill -g --all
```

Then say `/xy 新手入门` in your Agent to get going.

**Or clone and run the install script:**

```bash
git clone https://github.com/xyaz1313/xyskill.git && cd xyskill
bash install.sh
```

| Your tool | Skills directory |
|---|---|
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.agents/skills/` |
| Kimi Code | `~/.kimi-code/skills/` |
| Cursor / WorkBuddy / others | `~/.cursor/skills/` · `~/.workbuddy/skills/` · `~/.agents/skills/` |

**Or through the Claude Code plugin marketplace:**

```bash
claude plugin marketplace add https://github.com/xyaz1313/xyskill.git
claude plugin install xy@xy-skills
```

Use the full `https://` URL, not the `owner/repo` shorthand — the shorthand falls back to SSH and fails on machines without an SSH key configured for GitHub.

![Claude Code plugin install demo](demo.gif)

**Update:** already installed? Say `/xy-sync` to your Agent, or run `bash skills/xy-sync/scripts/xy-sync.sh sync`. Updates never touch your personal profile, archives, or decision records in `~/.xy/`.

Chinese is the system's native tongue, but it follows the language you use — ask in English, get English back.

## License

This repo is licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) (see `LICENSE`):

- Free for personal use, learning, research, and non-commercial projects.
- If you publish a derivative work, please credit the source.
- Commercial use requires separate licensing — contact the author below.

## Author & support

Author: **Xiaoye** · Serial entrepreneur & business creator · Author of Fengwu Zhishou · [Douyin](https://v.douyin.com/njWgCcCFUYY/)

<img src="docs/assets/wechat-qrcode.jpg" alt="WeChat" width="240">

Scan to connect on WeChat — for questions, commercial licensing or enterprise consulting.

---

<sub>This project's early routing and skill-skeleton design drew on some ideas from the open-source project [dbskill](https://github.com/dontbesilent2025/dbskill) (by dontbesilent, CC BY-NC 4.0), noted here for the record — no text, tweets, or knowledge data from it were used; all content and knowledge atoms are original to this project. Respect to Don't Be Silent 🙏</sub>
