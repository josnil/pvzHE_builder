# -*- coding: utf-8 -*-
"""verify_sway.py
校验 apply_sway.py 的落地结果：摇摆振幅属性覆盖条目（PropertyName="swayAmplitude"）是否正确、
是否同时适用于植物/僵尸/道具（共用一份 652 项白名单定义）、含 min/max/default/step 取值范围、
字节层规范、缩进、位置、幂等性与 config.zip 一致性；并确认误做的 phonkIntensity 已清除。

离线校验，不改任何文件（幂等性检测会临时调用 apply_sway.py，但其本身是 no-op，不改字节）。
退出码 0=全部通过，1=有失败项。
以 config.bak-sway/ 为基线比较「仅 sway 块」增量（=665 行，但因是就地替换 phonk 块，行数中性，增量=0），
避免硬编码行号。
"""
import hashlib
import io
import json
import os
import subprocess
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(BASE, "config")
BAK = os.path.join(BASE, "config.bak-sway")
TPL = os.path.join(CFG, "templates.json")
BAK_TPL = os.path.join(BAK, "templates.json")
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

print("[1] swayAmplitude 条目存在且唯一，phonkIntensity 已清除")
check(values.count("swayAmplitude") == 1,
      "swayAmplitude 唯一（出现 %d 次）" % values.count("swayAmplitude"))
check("swayAmplitude" in values, "包含 swayAmplitude 条目")
check("phonkIntensity" not in txt, "phonkIntensity 已从文件中完全清除（误做条目已替换）")
ph = [p for p in props if p.get("value") == "swayAmplitude"]
if ph:
    s = ph[0]
    print("\n[2] swayAmplitude 条目字段")
    for k in ("label", "value", "type", "default", "step", "min", "max",
              "placeholder", "helpTip", "whitelist"):
        check(k in s, "含字段 %s" % k)
    check(s.get("value") == "swayAmplitude",
          'value == "swayAmplitude"（实际 %r）' % s.get("value"))
    check(s.get("type") == "float", 'type == "float"（实际 %r）' % s.get("type"))
    check(s.get("label") == "摇摆振幅", 'label == "摇摆振幅"（实际 %r）' % s.get("label"))
    check("PropertyName" not in s,
          "无 PropertyName 字段（PropertyName 是导出时的键，模板只写 value）")
    print("\n[3] 约束：含取值范围 min/max/default/step")
    check(s.get("min") == 0, "min == 0（实际 %r）" % s.get("min"))
    check(s.get("max") == 1.5, "max == 1.5（实际 %r）" % s.get("max"))
    check(s.get("default") == 0, "default == 0（实际 %r）" % s.get("default"))
    check(s.get("step") == 0.05, "step == 0.05（实际 %r）" % s.get("step"))
    check(isinstance(s.get("min"), (int, float)) and isinstance(s.get("max"), (int, float)),
          "min/max 为数值类型")
    print("\n[4] 白名单：652 项，与 modulate/z_index/rotation/skew 同源同序、含全实体")
    wl = s.get("whitelist", [])
    check(len(wl) == 652, "whitelist 长度 = 652（实际 %d）" % len(wl))
    for other in ("z_index", "rotation", "modulate", "skew"):
        o = [p for p in props if p.get("value") == other]
        if o:
            check(wl == o[0]["whitelist"],
                  "与 %s.whitelist 逐项同序相等（同一份定义，植物/僵尸/道具共用）" % other)
    OPT = os.path.join(CFG, "options.json")
    if os.path.isfile(OPT):
        opt = json.loads(io.open(OPT, encoding="utf-8").read())
        union = []
        for key in ("plant", "zombie", "zombieExtra", "item"):
            union.extend(e["value"] for e in opt.get(key, []))
        check(wl == union, "等于 options.json plant+zombie+zombieExtra+item 按序并集（同序）")
        check("PlantPeaShooter" in wl and "ZombieNormal" in wl and "ItemBrain" in wl,
              "白名单覆盖植物 / 僵尸 / 道具代表项（均可复用同一 swayAmplitude 定义）")

    print("\n[5] 字节层：CRLF / 无裸LF / 无BOM / 结尾")
    crlf = raw.count(b"\r\n")
    bare_lf = raw.count(b"\n") - crlf
    check(bare_lf == 0, "无裸 LF（实际 %d）" % bare_lf)
    check(raw[:3] != b"\xef\xbb\xbf", "无 BOM")
    check(txt.endswith("}" + NL), "文件以 }%r 结尾" % NL)
    if os.path.isfile(BAK_TPL):
        braw = read_bytes(BAK_TPL)
        delta = crlf - braw.count(b"\r\n")
        # sway 块是就地替换 phonk 块，结构同为 { + 9键 + whitelist[ + 652项 + ] + } = 665 行，
        # 故相对 baseline(config.bak-sway 含 phonk) 的 CRLF 增量 = 0（行数中性）。
        check(delta == 0,
              "CRLF 增量 = 0（sway 就地替换 phonk 块，行数中性，实际 %d）" % delta)
        check(raw.count(b"\t") == braw.count(b"\t"), "tab 总数未增加")
    else:
        print("  NOTE 未找到基线备份 config.bak-sway，跳过增量比较")

    print("\n[6] sway 块缩进规范（8/12/16）且零 tab")
    lines = txt.split(NL)
    vidx = next((k for k, l in enumerate(lines) if '"value": "swayAmplitude"' in l), None)
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
        check(False, "未定位到 sway 块")

print("\n[7] swayAmplitude 位于 property 数组末尾（最新条目）")
check(props[-1].get("value") == "swayAmplitude",
      "末元素为 swayAmplitude（实际 %r）" % props[-1].get("value"))
from collections import Counter
KNOWN_DUPS = {"fireNum", "spawnList", "restTime", "speed"}
dups = set(k for k, n in Counter(values).items() if n > 1)
check(dups == KNOWN_DUPS, "重复 value 仍恰为已知 4 组 %s（实际 %s）"
      % (sorted(KNOWN_DUPS), sorted(dups)))

print("\n[8] 幂等性：重跑 apply_sway.py 不改 templates.json 字节")
m0 = md5(TPL)
r = subprocess.run(["python", "apply_sway.py"], cwd=BASE, capture_output=True, text=True)
check(r.returncode == 0, "apply_sway.py 重跑退出码 0（stderr=%s）"
      % (r.stderr.strip()[:80] or "空"))
m1 = md5(TPL)
check(m0 == m1, "重跑后 templates.json md5 不变（%s）" % m0)
check("already converted" in r.stdout, "apply_sway.py 命中幂等分支（already converted）")

print("\n[9] config.zip 一致性")
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
