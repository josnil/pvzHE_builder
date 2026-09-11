# -*- coding: utf-8 -*-
"""verify_z_index.py
校验 apply_z_index.py 的落地结果：结构、白名单、字节层（CRLF/BOM/结尾）、缩进、zip 一致性、
以及新构建器（gemmatch_builder）是否已同步到 z_index。

离线校验，不改任何文件。退出码 0=全部通过，1=有失败项。
以 config.bak-zindex/ 为基线比较字节层增量，避免硬编码行号。
"""
import io
import json
import os
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(BASE, "config")
BAK = os.path.join(BASE, "config.bak-zindex")
TPL = os.path.join(CFG, "templates.json")
BAK_TPL = os.path.join(BAK, "templates.json")
OPT = os.path.join(CFG, "options.json")
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


print("[1] 结构：property 条目与唯一性")
raw = read_bytes(TPL)
txt = raw.decode("utf-8")
tpl = json.loads(txt)
props = tpl["property"]
# 注意：不要用「恰好 40 条」这类硬编码断言——后续再追加属性条目（如 modulate）会误报。
# 本脚本职责是验证 z_index 本身正确，故只断言总数不倒退 + 与基线的增量自洽。
check(len(props) >= 42, "property 条目数 >= 42（实际 %d）" % len(props))
values = [p.get("value") for p in props]
if os.path.isfile(BAK_TPL):
    bak_n = len(json.loads(read_bytes(BAK_TPL).decode("utf-8"))["property"])
    check(len(props) == bak_n + 1 + (1 if "modulate" in values else 0)
          + (1 if "skew" in values else 0) + (1 if "swayAmplitude" in values else 0)
          + (1 if "modulateCycle" in values else 0),
          "条目数与基线自洽（基线 %d + z_index + modulate? + skew? + swayAmplitude? + modulateCycle? = %d）"
          % (bak_n, len(props)))
# 注意：property 数组历史上就存在 4 组同名 value（ka() 按 value 去重保首条的既有 quirk），
# 因此不能用「全部唯一」做断言；正确断言是「重复集合恰为这 4 组，且 z_index 不冲突」。
from collections import Counter
KNOWN_DUPS = {"fireNum", "spawnList", "restTime", "speed"}
cnt = Counter(values)
dups = set(k for k, n in cnt.items() if n > 1)
check(dups == KNOWN_DUPS, "重复 value 恰为已知 4 组 %s（实际 %s）"
      % (sorted(KNOWN_DUPS), sorted(dups)))
check(cnt.get("z_index") == 1, "z_index 唯一、与既有条目无冲突（出现 %d 次）"
      % cnt.get("z_index", 0))
check("z_index" in values, "包含 z_index 条目")

print("\n[2] z_index 条目字段")
zi = [p for p in props if p.get("value") == "z_index"]
check(len(zi) == 1, "z_index 条目唯一")
if zi:
    z = zi[0]
    for k in ("label", "value", "type", "whitelist"):
        check(k in z, "含字段 %s" % k)
    check(z.get("type") == "int", 'type == "int"（实际 %r）' % z.get("type"))
    check(z.get("min") == -4096, "min == -4096（实际 %r）" % z.get("min"))
    check(z.get("max") == 4096, "max == 4096（实际 %r）" % z.get("max"))
    check(z.get("default") == 0, "default == 0（实际 %r）" % z.get("default"))

print("\n[3] 白名单：与 rotation 同序、与 options.json 四数组并集一致")
wl = zi[0].get("whitelist", []) if zi else []
check(len(wl) == 652, "whitelist 长度 = 652（实际 %d）" % len(wl))
rot = [p for p in props if p.get("value") == "rotation"]
if rot:
    check(wl == rot[0]["whitelist"], "与 rotation.whitelist 逐项同序相等")
opt = json.loads(io.open(OPT, encoding="utf-8").read())
union = []
for key in ("plant", "zombie", "zombieExtra", "item"):
    union.extend(e["value"] for e in opt.get(key, []))
check(wl == union, "等于 options.json plant+zombie+zombieExtra+item 按序并集")

print("\n[4] 字节层：CRLF / 无裸LF / 无BOM / 结尾未破坏")
NL = "\r\n"
crlf = raw.count(b"\r\n")
bare_lf = raw.count(b"\n") - crlf
check(bare_lf == 0, "无裸 LF（实际 %d）" % bare_lf)
check(raw[:3] != b"\xef\xbb\xbf", "无 BOM")
check(txt.endswith("}" + NL), "文件以 }%r 结尾" % NL)
if os.path.isfile(BAK_TPL):
    braw = read_bytes(BAK_TPL)
    delta = crlf - braw.count(b"\r\n")
    # z_index 块 = { + 9键 + whitelist[ + 652项 + ] + } = 665 行
    expect = 1 + 9 + 1 + 652 + 1 + 1
    extra = ""
    if "modulate" in values:
        # modulate 块 = { + 6键(含 options) + whitelist[ + 652项 + ] + } = 662 行
        expect += 1 + 6 + 1 + 652 + 1 + 1
        extra = " + modulate 662"
    if "skew" in values:
        # skew 块 = { + 5键 + whitelist[ + 652项 + ] + } = 661 行
        expect += 1 + 5 + 1 + 652 + 1 + 1
        extra += " + skew 661"
    if "swayAmplitude" in values:
        # sway 块 = { + 9键 + whitelist[ + 652项 + ] + } = 665 行
        expect += 1 + 9 + 1 + 652 + 1 + 1
        extra += " + swayAmplitude 665"
    if "modulateCycle" in values:
        # modulateCycle 块 = { + 9键 + whitelist[ + 652项 + ] + } = 665 行
        expect += 1 + 9 + 1 + 652 + 1 + 1
        extra += " + modulateCycle 665"
    check(delta == expect,
          "CRLF 增量 = %d（z_index 665%s，实际 %d）" % (expect, extra, delta))
else:
    print("  NOTE 未找到基线备份，跳过增量比较")

print("\n[5] 新块缩进规范（8/12/16）且零 tab")
lines = txt.split(NL)
vidx = next((k for k, l in enumerate(lines) if '"value": "z_index"' in l), None)
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
    check(False, "未定位到 z_index 块")

print("\n[6] config.zip 一致性")
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

print("\n[7] 新构建器 gemmatch_builder 是否已同步")
if os.path.isfile(HTML):
    h = io.open(HTML, encoding="utf-8").read()
    check('"z_index"' in h, "gemmatch_builder.html 内嵌数据含 z_index")
    if '"z_index"' in h:
        m = h.split('<script id="DATA" type="application/json">')[1].split("</script>")[0]
        d = json.loads(m)
        zz = [p for p in d["property"] if p.get("value") == "z_index"]
        check(len(zz) == 1, "gemmatch 内嵌 z_index 条目唯一")
        if zz:
            check(len(zz[0].get("whitelist", [])) == 652,
                  "gemmatch 内嵌 z_index whitelist = 652（实际 %d）"
                  % len(zz[0].get("whitelist", [])))
else:
    print("  NOTE gemmatch_builder.html 不存在，跳过")

print("\n结果: " + ("全部通过" if not fails else "失败 %d 项" % len(fails)))
raise SystemExit(1 if fails else 0)
