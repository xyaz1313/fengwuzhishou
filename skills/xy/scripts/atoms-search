#!/usr/bin/env python3
"""薄封装：转调仓库根 scripts/atoms-search。按本文件的真实路径定位仓库（软链宿主也能用）。"""
import os,sys,runpy
root=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
target=os.path.join(root,"scripts","atoms-search")
if not os.path.isfile(target):
    print(f"[atoms-search] 找不到 {target}，请检查安装（skill 目录须软链自完整仓库）",file=sys.stderr); sys.exit(0)
sys.argv[0]=target; runpy.run_path(target,run_name="__main__")
