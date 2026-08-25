#!/usr/bin/env bash
# XY 首启/每次会话初始化：建 ~/.xy，输出档案摘要给宿主注入上下文。任何失败静默退出。
set -uo pipefail
XY="${XY_HOME:-$HOME/.xy}"
mkdir -p "$XY/sessions" "$XY/decisions" "$XY/reports" 2>/dev/null || exit 0
if [ ! -f "$XY/config.json" ]; then
  cat > "$XY/config.json" <<'JSON'
{ "version": 1, "brain": "host", "external_api": { "provider": "", "base_url": "", "model": "", "api_key_env": "" }, "first_run_done": false }
JSON
fi
# 记录安装根目录（原子检索兜底用）；档案已存在则标记首启完成
ROOT="$(cd "$(dirname "$(python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$0")")/.." && pwd -P)"
python3 - "$XY/config.json" "$ROOT" "$XY/profile.md" <<'PY' 2>/dev/null || true
import json,sys,os
p,root,prof=sys.argv[1:4]
try: c=json.load(open(p,encoding="utf-8"))
except Exception: c={"version":1,"brain":"host","external_api":{"provider":"","base_url":"","model":"","api_key_env":""}}
c["root"]=root; c["first_run_done"]=os.path.isfile(prof)
json.dump(c,open(p,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
PY
if [ -f "$XY/profile.md" ]; then
  echo "[XY 教练档案摘要]"; head -40 "$XY/profile.md"
else
  echo "[XY 教练] 尚无用户档案。用户第一次开口时，xy-coach 先做 ≤5 问的首次访谈并写入 ~/.xy/profile.md，再路由。"
fi
exit 0
