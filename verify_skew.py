# -*- coding: utf-8 -*-
"""verify_skew.py
校验 apply_skew.py 的落地结果：skew 属性覆盖条目（PropertyName="skew"）是否正确、是否同时适用于植物/僵尸
（共用一份 652 项白名单定义）、字节层规范、缩进、位置、幂等性与 config.zip 一致性。

离线校验，不改任何文件（幂等性检测会临时调用 apply_skew.py，但其本身是 no-op，不改字节）。
退出码 0=全部通过，1=有失败项。
以 config.bak-skew/ 为基线比较「仅 skew 块」增量（=662 行），避免硬编码行号。
"""
import hashlib
import io
import json
import os
import subprocess
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(BASE, "config")
BAK = os.path.join(BASE, "config.bak-skew")
TPL = os.path.join(CFG, "templates.json")
BAK_TPL = os.path.join(BAK, "templates.json")
ZIP = os.path.join(CFG, "config.zip")
HTML = os.path.join(BASE, "gemmatch_builder.html")

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

print("[1] skew 条目存在且唯一")
check(values.count("skew") == 1, "skew 唯一（出现 %d 次）" % values.count("skew"))
check("skew" in values, "包含 skew 条目")
sk = [p for p in props if p.get("value") == "skew"]
if sk:
    s = sk[0]
    print("\n[2] skew 条目字段")
    for k in ("label", "value", "type", "placeholder", "helpTip", "whitelist"):
        check(k in s, "含字段 %s" % k)
    check(s.get("value") == "skew", 'value == "skew"（实际 %r）' % s.get("value"))
    check(s.get("type") == "float", 'type == "float"（实际 %r）' % s.get("type"))
    check("PropertyName" not in s, "无 PropertyName 字段（PropertyName 是导出时的键，模板只写 value）")
    for k in ("default", "min", "max", "step"):
        check(k not in s, "不含 %s（与 rotation/z_index/modulate 一致，值由关卡 JSON 填写）" % k)
    check("弧度" in (s.get("helpTip") or "") and "90" in (s.get("helpTip") or ""),
          "helpTip 提示弧度单位与 90 弧度陷阱")
    check("1.5708" in (s.get("placeholder") or ""), "placeholder 给出 90°→弧度 换算示例")

    print("\n[3] 白名单：652 项、与 z_index/rotation/modulate 同源同序、含全实体")
    wl = s.get("whitelist", [])
    check(len(wl) == 652, "whitelist 长度 = 652（实际 %d）" % len(wl))
    for other in ("z_index", "rotation", "modulate"):
        o = [p for p in props if p.get("value") == other]
        if o:
            check(wl == o[0]["whitelist"],
                  "与 %s.whitelist 逐项同序相等（同一份定义，植物/僵尸共用）" % other)
    # 植物 ∪ 僵尸 ∪ 僵尸Extra ∪ 道具 在 options.json 中的并集
    OPT = os.path.join(CFG, "options.json")
    if os.path.isfile(OPT):
        opt = json.loads(io.open(OPT, encoding="utf-8").read())
        union = []
        for key in ("plant", "zombie", "zombieExtra", "item"):
            union.extend(e["value"] for e in opt.get(key, []))
        check(wl == union, "等于 options.json plant+zombie+zombieExtra+item 按序并集（同序）")
        # 至少含若干代表：植物 / 僵尸 / 道具
        check("PlantPeaShooter" in wl and "ZombieNormal" in wl and "ItemBrain" in wl,
              "白名单覆盖植物 / 僵尸 / 道具代表项（均可复用同一 skew 定义）")

    print("\n[4] 字节层：CRLF / 无裸LF / 无BOM / 结尾")
    crlf = raw.count(b"\r\n")
    bare_lf = raw.count(b"\n") - crlf
    check(bare_lf == 0, "无裸 LF（实际 %d）" % bare_lf)
    check(raw[:3] != b"\xef\xbb\xbf", "无 BOM")
    check(txt.endswith("}" + NL), "文件以 }%r 结尾" % NL)
    if os.path.isfile(BAK_TPL):
        braw = read_bytes(BAK_TPL)
        delta = crlf - braw.count(b"\r\n")
        # skew 块 = { + 5键 + whitelist[ + 652项 + ] + } = 661 行
        expect = 1 + 5 + 1 + 652 + 1 + 1
        check(delta >= expect,
              "CRLF 增量 >= %d（skew 块 661 行，含后续追加块只增不减，实际 %d）" % (expect, delta))
        check(raw.count(b"\t") == braw.count(b"\t"), "tab 总数未增加")
    else:
        print("  NOTE 未找到基线备份 config.bak-skew，跳过增量比较")

    print("\n[5] skew 块缩进规范（8/12/16）且零 tab")
    lines = txt.split(NL)
    vidx = next((k for k, l in enumerate(lines) if '"value": "skew"' in l), None)
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
        check(False, "未定位到 skew 块")

print("\n[6] skew 位于 property 数组末尾（最新追加）")
check(props[-1].get("value") in ("skew", "swayAmplitude", "modulateCycle"),
      "末元素为 skew / swayAmplitude / modulateCycle（最新追加，实际 %r）" % props[-1].get("value"))
# 注意：历史上 property 存在 4 组同名 value（ka() 去重保首条的 quirk），不要求全部唯一
from collections import Counter
KNOWN_DUPS = {"fireNum", "spawnList", "restTime", "speed"}
dups = set(k for k, n in Counter(values).items() if n > 1)
check(dups == KNOWN_DUPS, "重复 value 仍恰为已知 4 组 %s（实际 %s）"
      % (sorted(KNOWN_DUPS), sorted(dups)))

print("\n[7] 幂等性：重跑 apply_skew.py 不改 templates.json 字节")
m0 = md5(TPL)
r = subprocess.run(["python", "apply_skew.py"], cwd=BASE, capture_output=True, text=True)
check(r.returncode == 0, "apply_skew.py 重跑退出码 0（stderr=%s）"
      % (r.stderr.strip()[:80] or "空"))
m1 = md5(TPL)
check(m0 == m1, "重跑后 templates.json md5 不变（%s）" % m0)
check("already patched" in r.stdout, "apply_skew.py 命中幂等分支（already patched）")

print("\n[8] config.zip 一致性")
if os.path.isfile(ZIP):
    with zipfile.ZipFile(ZIP) as z:
        names = z.namelist()
        check(sorted(names) == sorted(["options.json", "templates.json",
                                       "default.json", "validate.js"]),
              "zip 含 4 个文件且无目录前缀")
        check(all("/" not in n for n in names), "arcname 均无目录前缀")
        check(z.read("templates.json") == raw, "zip 内 templates.json 与磁盘字节一致")
else:
    check(False, "config.zip 不存在")

print("\n结果: " + ("全部通过" if not fails else "失败 %d 项" % len(fails)))
raise SystemExit(1 if fails else 0)
