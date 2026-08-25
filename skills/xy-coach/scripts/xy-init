#!/usr/bin/env bash
# 薄封装：按本文件的真实路径找到仓库根，转调 scripts/xy-init.sh（软链宿主也能用）
SELF="$(python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SELF")/../../.." && pwd -P)"
exec bash "$ROOT/scripts/xy-init.sh" "$@"
