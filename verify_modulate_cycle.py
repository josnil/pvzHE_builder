# -*- coding: utf-8 -*-
"""verify_modulate_cycle.py
校验 apply_modulate_cycle.py 的落地结果：modulateCycle 属性覆盖条目
（PropertyName="modulateCycle"，固定7色循环 + 速度）是否正确、是否同时适用于植物/僵尸
（共用一份 652 项白名单定义）、字节层规范、缩进、位置、幂等性与 config.zip 一致性。

离线校验，不改任何文件（幂等性检测会临时调用 apply_modulate_cycle.py，但其本身是 no-op，不改字节）。
退出码 0=全部通过，1=有失败项。
"""
import hashlib
import io
import json
import os
import subprocess
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(BASE, "config")
TPL = os.path.join(CFG, "templates.json")
ZIP = os.path.join(CFG, "config.zip")

fails = []


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


def read_bytes(p):
    with io.open(p, "rb") as f:
        return f.read()


def md5(p):
    return hashlib.md5(read_bytes(p)).hexdigest()


NL = "\r\n"
raw = read_bytes(TPL)
txt = raw.decode("utf-8")
tpl = json.loads(txt)
props = tpl["property"]
values = [p.get("value") for p in props]

print("[1] property 条目总数与 modulateCycle 存在且唯一")
check(len(props) == 44, "property 条目数 = 44（实际 %d）" % len(props))
check(values.count("modulateCycle") == 1, "modulateCycle 唯一（出现 %d 次）" % values.count("modulateCycle"))
check("modulateCycle" in values, "包含 modulateCycle 条目")
mc = [p for p in props if p.get("value") == "modulateCycle"]
if mc:
    m = mc[0]
    print("\n[2] modulateCycle 条目字段")
    for k in ("label", "value", "type", "default", "step", "min", "max", "placeholder", "helpTip", "whitelist"):
        check(k in m, "含字段 %s" % k)
    check(m.get("value") == "modulateCycle", 'value == "modulateCycle"（实际 %r）' % m.get("value"))
    check(m.get("type") == "float", 'type == "float"（实际 %r）' % m.get("type"))
    check(m.get("default") == 0, "default == 0（关闭，实际 %r）" % m.get("default"))
    check(m.get("min") == 0, "min == 0（实际 %r）" % m.get("min"))
    check(m.get("max") == 5, "max == 5（实际 %r）" % m.get("max"))
    check(m.get("step") == 0.1, "step == 0.1（实际 %r）" % m.get("step"))
    check("PropertyName" not in m, "无 PropertyName 字段（PropertyName 是导出键，模板只写 value）")
    ht = m.get("helpTip") or ""
    check("红" in ht and "粉" in ht and "紫" in ht and "绿" in ht and "蓝" in ht and "橙" in ht and "黄" in ht,
          "helpTip 含固定7色调色板说明（红粉紫绿蓝橙黄）")
    check("ColorCycleComponent" in ht and "只读" in ht,
          "helpTip 注明游戏侧 ColorCycleComponent 缺口（.cs 只读，待补）")

    print("\n[3] 白名单：652 项、与 z_index/swayAmplitude 同源同序、含全实体")
    wl = m.get("whitelist", [])
    check(len(wl) == 652, "whitelist 长度 = 652（实际 %d）" % len(wl))
    for other in ("z_index", "swayAmplitude", "modulate"):
        o = [p for p in props if p.get("value") == other]
        if o:
            check(wl == o[0]["whitelist"],
                  "与 %s.whitelist 逐项同序相等（同一份定义，植物/僵尸共用）" % other)
    OPT = os.path.join(CFG, "options.json")
    if os.path.isfile(OPT):
        opt = json.loads(io.open(OPT, encoding="utf-8").read())
        union = []
        for key in ("plant", "zombie", "zombieExtra", "item"):
            union.extend(e["value"] for e in opt.get(key, []))
        check(wl == union, "等于 options.json plant+zombie+zombieExtra+item 按序并集（同序）")
        check("PlantPeaShooter" in wl and "ZombieNormal" in wl and "ItemBrain" in wl,
              "白名单覆盖植物 / 僵尸 / 道具代表项")

    print("\n[4] 字节层：CRLF / 无裸LF / 无BOM / 结尾")
    crlf = raw.count(b"\r\n")
    bare_lf = raw.count(b"\n") - crlf
    check(bare_lf == 0, "无裸 LF（实际 %d）" % bare_lf)
    check(raw[:3] != b"\xef\xbb\xbf", "无 BOM")
    check(txt.endswith("}" + NL), "文件以 }%r 结尾" % NL)

    print("\n[5] 新块缩进规范（8/12/16）且零 tab")
    lines = txt.split(NL)
    vidx = next((k for k, l in enumerate(lines) if '"value": "modulateCycle"' in l), None)
    if vidx is not None:
        K = len(lines[vidx]) - len(lines[vidx].lstrip())
        check(K == 12, "键名缩进 = 12（实际 %d）" % K)
        oi = vidx - 1
        while oi >= 0 and lines[oi].strip() != "{":
            oi -= 1
        P = len(lines[oi]) - len(lines[oi].lstrip()) if oi >= 0 else -1
        check(P == 8, "元素 { 缩进 = 8（实际 %d）" % P)
        wi = next(k for k in range(vidx, len(lines)) if '"whitelist": [' in lines[k])
        W = len(lines[wi + 1]) - len(lines[wi + 1].lstrip())
        check(W == 16, "whitelist 项缩进 = 16（实际 %d）" % W)
        block = lines[oi:wi + 654]
        check(all("\t" not in l for l in block), "新块内零 tab")
    else:
        check(False, "未定位到 modulateCycle 块")

print("\n[6] modulateCycle 位于 property 数组末尾（最新追加）")
check(props[-1].get("value") in ("skew", "swayAmplitude", "modulateCycle"),
      "末元素为 skew / swayAmplitude / modulateCycle（最新追加，实际 %r）" % props[-1].get("value"))
from collections import Counter
KNOWN_DUPS = {"fireNum", "spawnList", "restTime", "speed"}
dups = set(k for k, n in Counter(values).items() if n > 1)
check(dups == KNOWN_DUPS, "重复 value 仍恰为已知 4 组 %s（实际 %s）" % (sorted(KNOWN_DUPS), sorted(dups)))

print("\n[7] 幂等性：重跑 apply_modulate_cycle.py 不改 templates.json 字节")
m0 = md5(TPL)
r = subprocess.run(["python", "apply_modulate_cycle.py"], cwd=BASE, capture_output=True, text=True)
check(r.returncode == 0, "apply 重跑退出码 0（stderr=%s）" % (r.stderr.strip()[:80] or "空"))
m1 = md5(TPL)
check(m0 == m1, "重跑后 templates.json md5 不变（%s）" % m0)
check("already patched" in r.stdout, "apply 命中幂等分支（already patched）")

print("\n[8] config.zip 一致性")
if os.path.isfile(ZIP):
    with zipfile.ZipFile(ZIP) as z:
        names = z.namelist()
        check(sorted(names) == sorted(["options.json", "templates.json", "default.json", "validate.js"]),
              "zip 含 4 个文件且无目录前缀")
        check(all("/" not in n for n in names), "arcname 均无目录前缀")
        check(z.read("templates.json") == raw, "zip 内 templates.json 与磁盘字节一致")
else:
    check(False, "config.zip 不存在")

print("\n结果: " + ("全部通过" if not fails else "失败 %d 项" % len(fails)))
raise SystemExit(1 if fails else 0)
