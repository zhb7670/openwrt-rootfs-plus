#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
science_guard.py —— 「科学插件保真」预检工具（只用标准库，CI 里 python3 直接跑）

三个子命令：

  check-rootfs   检查 rootfs(tar.gz) 里 5 个科学插件及其内核模块依赖闭包
                 并导出 ko_list.txt（后续核对内核用）
  check-kernel   按内核系列（如 6.1）取 ophub/kernel 的 flippy 内核包，
                 核对 ko_list.txt 里的 .ko 是否"模块里有 或 内核内建"
  merge-status   把供体 rootfs 的 opkg/status 中指定包的段落合并进目标 rootfs
                 （仅在线下/备用移植路径里用）

设计原则：任何一项对不上就以非 0 退出，宁可失败也不产出"缺插件"的固件。
"""
import argparse
import io
import json
import os
import re
import sys
import tarfile
import urllib.request

OphubKernelApi = "https://api.github.com/repos/ophub/kernel/releases/tags/kernel_flippy"

# 文件级移植的安全红线：这些包不能靠"拷文件"补
DENY = re.compile(
    r"^(kernel|base-files|busybox|opkg|libc|libgcc\d*|libpthread|librt|"
    r"ubus|libubox\d*|libubus\d*|uci|libuci\d*|netifd|firewall\d*|nftables|"
    r"libnftnl\d*|libmnl\d*|libnfnetlink\d*|iptables|ip6tables|libxtables\d*|"
    r"libip4tc\d*|libip6tc\d*|dnsmasq.*|kmod-.*)$"
)


# --------------------------------------------------------------------------
# 公共：读 tar.gz 里的某个成员 / 解析 opkg status
# --------------------------------------------------------------------------
def read_member(path, suffix):
    with tarfile.open(path, "r|gz") as tf:
        for m in tf:
            if m.isfile() and m.name.endswith(suffix):
                return tf.extractfile(m).read().decode("utf-8", "replace")
    return None


def parse_status(text):
    pkgs = {}
    order = []
    for blk in text.split("\n\n"):
        d = {}
        for line in blk.splitlines():
            if ": " in line:
                k, v = line.split(": ", 1)
                d[k.strip()] = v.strip()
        if d.get("Package"):
            pkgs[d["Package"]] = d
            order.append(d["Package"])
    return pkgs, order


def norm_dep(tok):
    tok = tok.split("|")[0].strip()
    tok = re.sub(r"\s*\(.*?\)\s*$", "", tok).strip()
    return tok


def closure(pkgs, roots):
    seen, stack = set(roots), list(roots)
    while stack:
        c = stack.pop()
        for tok in pkgs.get(c, {}).get("Depends", "").split(","):
            d = norm_dep(tok)
            if d and d in pkgs and d not in seen:
                seen.add(d)
                stack.append(d)
    return seen


# --------------------------------------------------------------------------
# check-rootfs
# --------------------------------------------------------------------------
def cmd_check_rootfs(a):
    status = read_member(a.rootfs, "usr/lib/opkg/status")
    if not status:
        print("::error::在 %s 里找不到 usr/lib/opkg/status" % a.rootfs)
        return 1
    pkgs, _ = parse_status(status)
    print(">>> rootfs 已装包总数: %d" % len(pkgs))

    want = [x for x in a.pkgs.split() if x]
    missing = [x for x in want if x not in pkgs]

    print("\n>>> 指定的科学插件在 rootfs 中的情况：")
    for x in want:
        p = pkgs.get(x)
        if p:
            print("    [有] %-32s %s" % (x, p.get("Version", "")))
        else:
            print("    [缺] %-32s —— 不在 rootfs 里" % x)

    if missing:
        print("\n::error::目标 rootfs 缺少这些科学插件: %s" % " ".join(missing))
        print("          请把 donor_asset 填成「含这些插件的 rootfs」所在的 Release 资产名，")
        print("          走工作流的「移植补救」步骤；或改用正确的 rootfs_asset。")
        with open(a.out, "w", encoding="utf-8") as f:
            f.write("STATUS=MISSING\n")
            f.write("MISSING=%s\n" % " ".join(missing))
        return 1

    # 依赖闭包里的 kmod
    need = {}
    for root in want:
        for n in sorted(closure(pkgs, [root])):
            if n.startswith("kmod-"):
                need.setdefault(n, set()).add(root)
    print("\n>>> 这 %d 个插件依赖的 kmod 包: %d 个" % (len(want), len(need)))

    # 从 rootfs 的 opkg/info/<pkg>.list 里取 .ko 名字
    ko_list = []
    ko_by_pkg = {}
    with tarfile.open(a.rootfs, "r|gz") as tf:
        for m in tf:
            if not m.isfile():
                continue
            mm = re.search(r"usr/lib/opkg/info/(.+)\.list$", m.name)
            if not mm or mm.group(1) not in need:
                continue
            body = tf.extractfile(m).read().decode("utf-8", "replace")
            kos = sorted({os.path.basename(x) for x in body.splitlines() if x.endswith(".ko")})
            ko_by_pkg[mm.group(1)] = kos
            ko_list.extend(kos)

    print("\n>>> 插件真正需要的内核模块 .ko（共 %d 个）:" % len(ko_list))
    for pkg in sorted(ko_by_pkg):
        print("    %-34s %s" % (pkg, " ".join(ko_by_pkg[pkg])))

    with open(a.ko_out, "w", encoding="utf-8") as f:
        for ko in sorted(set(ko_list)):
            f.write(ko + "\n")

    with open(a.out, "w", encoding="utf-8") as f:
        f.write("STATUS=OK\n")
        f.write("PKGS=%s\n" % " ".join(want))
        f.write("KMOD_COUNT=%d\n" % len(need))
        f.write("KO_COUNT=%d\n" % len(set(ko_list)))
        f.write("KO_FILE=%s\n" % a.ko_out)

    print("\n>>> 预检通过：5 个科学插件都在 rootfs 里；.ko 清单已写入 %s" % a.ko_out)
    return 0


# --------------------------------------------------------------------------
# check-kernel
# --------------------------------------------------------------------------
def http_json(url):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", "Bearer %s" % tok)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def latest_kernel_asset(series):
    rel = http_json(OphubKernelApi)
    pat = re.compile(r"^%s\.[0-9]+\.tar\.gz$" % re.escape(series))
    cands = []
    for a in rel.get("assets", []):
        if pat.match(a["name"]):
            cands.append(([int(x) for x in re.findall(r"\d+", a["name"][:-7])], a))
    if not cands:
        raise SystemExit("::error::ophub/kernel 的 kernel_flippy 里找不到 %s.x 内核" % series)
    cands.sort(key=lambda x: x[0])
    return cands[-1][1]


def cmd_check_kernel(a):
    asset = latest_kernel_asset(a.series)
    print(">>> 内核系列 %s -> ophub/kernel/kernel_flippy/%s (%.1f MB)"
          % (a.series, asset["name"], asset["size"] / 1048576.0))
    if a.kernel and os.path.exists(a.kernel):
        path = a.kernel
    else:
        path = os.path.join(a.workdir, asset["name"])
        if not os.path.exists(path):
            print(">>> 下载 %s ..." % asset["name"])
            url = asset["browser_download_url"]
            req = urllib.request.Request(url)
            tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
            if tok:
                req.add_header("Authorization", "Bearer %s" % tok)
            with urllib.request.urlopen(req, timeout=600) as r, open(path, "wb") as f:
                while True:
                    buf = r.read(1 << 20)
                    if not buf:
                        break
                    f.write(buf)

    want = set()
    if os.path.exists(a.ko_file):
        with open(a.ko_file, encoding="utf-8") as f:
            want = {l.strip() for l in f if l.strip()}
    if not want:
        print("::error::%s 为空 —— 请先跑 check-rootfs" % a.ko_file)
        return 1
    print(">>> 待核对 .ko: %d 个" % len(want))

    mod_bytes = None
    mod_name = None
    with tarfile.open(path, "r|gz") as tf:
        for m in tf:
            if m.isfile() and re.search(r"modules-[\d.]+-flippy[^/]*\.tar\.gz$", m.name):
                mod_name = m.name
                mod_bytes = tf.extractfile(m).read()
                break
    if mod_bytes is None:
        print("::error::内核包里没有 modules-*.tar.gz")
        return 1
    have, builtin = set(), set()
    with tarfile.open(fileobj=io.BytesIO(mod_bytes), mode="r|gz") as t2:
        for m in t2:
            if m.name.endswith(".ko"):
                have.add(os.path.basename(m.name))
            if m.name.endswith("modules.builtin") and m.isfile():
                for l in t2.extractfile(m).read().decode("utf-8", "replace").splitlines():
                    builtin.add(os.path.basename(l.strip()))
    print(">>> %s: 模块 .ko %d 个 / builtin %d 个" % (mod_name, len(have), len(builtin)))

    miss = sorted(k for k in want if k not in have and k not in builtin)
    okm = sorted(k for k in want if k in have)
    okb = sorted(k for k in want if k not in have and k in builtin)
    print(">>> 命中：模块形式 %d 个，内建形式 %d 个" % (len(okm), len(okb)))
    if okb:
        print("    内建：%s" % " ".join(okb))
    if miss:
        print("\n::error::以下 .ko 在 %s 里既不是模块也不是内建：%s" % (asset["name"], " ".join(miss)))
        print("          说明这版内核跑不了对应的科学插件，请换内核系列或换插件版本。")
        return 1
    print("\n>>> 内核预检通过：%s 足以支撑这 5 个科学插件" % asset["name"])
    return 0


# --------------------------------------------------------------------------
# plan-port：算出"要补哪些包、要复制哪些文件"
# --------------------------------------------------------------------------
def cmd_plan_port(a):
    don_status = read_member(a.donor_tar, "usr/lib/opkg/status")
    tgt_status = read_member(a.target_tar, "usr/lib/opkg/status")
    if not don_status or not tgt_status:
        print("::error::供体或目标 rootfs 里找不到 usr/lib/opkg/status")
        return 1
    dp, _ = parse_status(don_status)
    tp, _ = parse_status(tgt_status)
    want = [x for x in a.pkgs.split() if x]
    missing = [x for x in want if x not in tp]

    print(">>> 目标 rootfs 已装包 %d 个，供体 %d 个" % (len(tp), len(dp)))
    print(">>> 需要补的插件: %s" % (" ".join(missing) if missing else "（没有，无需移植）"))

    if not missing:
        open(a.plan, "w").close()
        open(a.names, "w").close()
        print(">>> 无需移植：5 个插件本来就都在目标 rootfs 里")
        return 0

    # 闭包只取"目标里没有的"包，避免覆盖已有版本
    sel = set()
    for r in missing:
        if r not in dp:
            print("::error::供体 rootfs 里也没有 %s，无法移植" % r)
            return 1
        for n in closure(dp, [r]):
            if n not in tp:
                sel.add(n)
    sel |= set(missing)

    # 安全红线：这些包不能靠"拷文件"补 —— 它们有维护者脚本/alternatives/内核替换，
    # 必须由 opkg 或打包脚本处理，硬拷会做出开不了机或没法上网的固件。
    blocked = sorted(n for n in sel if DENY.match(n))
    if blocked:
        print("\n::error::以下依赖包不允许用文件级移植补装：")
        for n in blocked:
            print("    - %s" % n)
        print("          它们涉及 opkg 维护脚本 / alternatives / 内核模块替换，")
        print("          硬拷会破坏系统。请改装一个本来就带这些依赖的 rootfs（改 rootfs_asset）。")
        return 2

    print(">>> 通过安全红线检查（未触及 kernel/kmod/libc/iptables 等系统级包）")

    # 读供体的 .list，列出要复制的文件（含 usr/lib/opkg/info/<pkg>.* 元数据）
    names_to_read = set(sel)
    lists = {}
    info_files = {}
    with tarfile.open(a.donor_tar, "r|gz") as tf:
        for m in tf:
            if not m.isfile():
                continue
            mm = re.search(r"usr/lib/opkg/info/(.+)\.list$", m.name)
            if mm and mm.group(1) in names_to_read:
                lists[mm.group(1)] = tf.extractfile(m).read().decode("utf-8", "replace")
                continue
            mi = re.search(r"usr/lib/opkg/info/(.+)\.([A-Za-z0-9_\-]+)$", m.name)
            if mi and mi.group(1) in names_to_read:
                info_files.setdefault(mi.group(1), []).append(m.name.lstrip("./"))

    rows = []
    for pkg in sorted(sel):
        for line in lists.get(pkg, "").splitlines():
            line = line.strip()
            if not line or line.endswith("/"):
                continue
            if "*" in line:
                continue
            rel = line.lstrip("/")
            if not rel:
                continue
            rows.append((pkg, rel))
        for rel in sorted(set(info_files.get(pkg, []))):
            rows.append((pkg, rel))

    with open(a.plan, "w", encoding="utf-8") as f:
        for pkg, rel in rows:
            f.write("%s\t%s\n" % (pkg, rel))
    with open(a.names, "w", encoding="utf-8") as f:
        for pkg in sorted(sel):
            f.write(pkg + "\n")

    print(">>> 计划补装 %d 个包，涉及 %d 个文件（清单: %s / %s）"
          % (len(sel), len(rows), a.names, a.plan))
    print("    包清单: %s" % " ".join(sorted(sel)))
    return 0


# --------------------------------------------------------------------------
# merge-status（备用移植路径用）
# --------------------------------------------------------------------------
def split_stanzas(text):
    out = {}
    for blk in text.split("\n\n"):
        m = re.search(r"^Package:\s*(\S+)\s*$", blk, re.M)
        if m:
            out[m.group(1)] = blk.rstrip("\n")
    return out


def cmd_merge_status(a):
    txt = open(a.target, encoding="utf-8", errors="replace").read()
    _t, _ = parse_status(txt)
    don = read_member(a.donor_tar, "usr/lib/opkg/status")
    if not don:
        print("::error::供体 rootfs 里没有 opkg/status")
        return 1
    tst, dst = split_stanzas(txt), split_stanzas(don)

    names = [l.strip() for l in open(a.names, encoding="utf-8") if l.strip()] if os.path.exists(a.names) else []
    added, replaced = [], []
    for n in names:
        if n not in dst:
            print("    [跳过] 供体 status 里没有 %s" % n)
            continue
        if n in tst:
            replaced.append(n)
        else:
            added.append(n)
            txt = txt.rstrip("\n") + "\n\n" + dst[n] + "\n"
    # 写盘时锁死换行符：Windows 上 "w" 会把 \n 变成 \r\n，会毁掉 opkg 数据库
    with open(a.target, "w", encoding="utf-8", newline="") as f:
        f.write(txt)
    print(">>> status 合并完成：新增 %d 个，已存在(保持不动) %d 个" % (len(added), len(replaced)))
    if added:
        print("    新增条目：%s" % " ".join(added))
    return 0


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("check-rootfs")
    p1.add_argument("--rootfs", required=True)
    p1.add_argument("--pkgs", required=True)
    p1.add_argument("--out", default="/tmp/science-guard.txt")
    p1.add_argument("--ko-out", default="/tmp/science-ko.txt")
    p1.set_defaults(func=cmd_check_rootfs)

    p2 = sub.add_parser("check-kernel")
    p2.add_argument("--series", default="6.1")
    p2.add_argument("--ko-file", default="/tmp/science-ko.txt")
    p2.add_argument("--kernel", default="")
    p2.add_argument("--workdir", default="/tmp")
    p2.set_defaults(func=cmd_check_kernel)

    p3 = sub.add_parser("plan-port")
    p3.add_argument("--donor-tar", required=True)
    p3.add_argument("--target-tar", required=True)
    p3.add_argument("--pkgs", required=True)
    p3.add_argument("--plan", default="/tmp/port-plan.tsv")
    p3.add_argument("--names", default="/tmp/port-names.txt")
    p3.set_defaults(func=cmd_plan_port)

    p4 = sub.add_parser("merge-status")
    p4.add_argument("--target", required=True)
    p4.add_argument("--donor-tar", required=True)
    p4.add_argument("--names", required=True)
    p4.set_defaults(func=cmd_merge_status)

    a = ap.parse_args()
    sys.exit(a.func(a))


if __name__ == "__main__":
    main()
