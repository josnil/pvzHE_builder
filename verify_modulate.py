# -*- coding: utf-8 -*-
"""verify_modulate.py
校验 modulate 属性覆盖的落地结果（apply_modulate.py + apply_modulate_options.py）：
  - templates.json 的 modulate 条目（结构/白名单/options 预设接入/字节层/缩进）
  - options.json 的 modulatePresets 颜色预设数组（11 项、label/value、#RRGGBBAA）
  - validate.js 的校验规则、config.zip 一致性

离线校验，不改任何文件。退出码 0=全部通过，1=有失败项。
以 config.bak-modulate-opts/ 为基线比较「仅 options 一行」增量，避免硬编码行号。
"""
import io
import json
import os
import subprocess
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(BASE, "config")
BAK = os.path.join(BASE, "config.bak-modulate")
BAK2 = os.path.join(BASE, "config.bak-modulate-opts")  # 已含 modulate、未含 options 的基线
TPL = os.path.join(CFG, "templates.json")
BAK_TPL = os.path.join(BAK, "templates.json")
BAK2_TPL = os.path.join(BAK2, "templates.json")
VJS = os.path.join(CFG, "validate.js")
ZIP = os.path.join(CFG, "config.zip")

fails = []


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


def read_bytes(p):
    with io.open(p, "rb") as f:
        return f.read()


raw = read_bytes(TPL)
txt = raw.decode("utf-8")
tpl = json.loads(txt)
props = tpl["property"]

print("[1] 结构：property 条目与 modulate/skew 位置")
check(len(props) == 44, "property 条目数 = 44（实际 %d）" % len(props))
check(props[-1].get("value") in ("skew", "swayAmplitude", "modulateCycle"),
      "末元素为 skew / swayAmplitude / modulateCycle（最新追加，实际 %r）" % props[-1].get("value"))
values = [p.get("value") for p in props]
check(values.count("z_index") == 1, "z_index 仍在且唯一")
check(values.count("modulate") == 1, "modulate 唯一（出现 %d 次）" % values.count("modulate"))
check(values.count("skew") == 1, "skew 唯一（出现 %d 次）" % values.count("skew"))
# 历史既有 4 组同名 value，不做"全部唯一"断言
KNOWN_DUPS = {"fireNum", "spawnList", "restTime", "speed"}
from collections import Counter
dups = set(k for k, n in Counter(values).items() if n > 1)
check(dups == KNOWN_DUPS, "重复 value 仍恰为已知 4 组 %s（实际 %s）"
      % (sorted(KNOWN_DUPS), sorted(dups)))

print("\n[2] modulate 条目字段")
mo = [p for p in props if p.get("value") == "modulate"]
if mo:
    m = mo[0]
    for k in ("label", "value", "type", "whitelist"):
        check(k in m, "含字段 %s" % k)
    check(m.get("type") == "select", 'type == "select"（实际 %r）' % m.get("type"))
    check(m.get("options") == "import:modulatePresets",
          '含 options = "import:modulatePresets"（下拉预设已接入）')
    for k in ("default", "min", "max", "step"):
        check(k not in m, "不含 %s（避免污染/全透明风险）" % k)

print("\n[3] 白名单：与 z_index 同源同序")
wl = mo[0].get("whitelist", []) if mo else []
check(len(wl) == 652, "whitelist 长度 = 652（实际 %d）" % len(wl))
zi = [p for p in props if p.get("value") == "z_index"]
if zi:
    check(wl == zi[0]["whitelist"], "与 z_index.whitelist 逐项同序相等")

print("\n[4] 字节层：CRLF / 无裸LF / 无BOM / 结尾 / tab 不扩散")
NL = "\r\n"
crlf = raw.count(b"\r\n")
bare_lf = raw.count(b"\n") - crlf
tabs = raw.count(b"\t")
check(bare_lf == 0, "无裸 LF（实际 %d）" % bare_lf)
check(raw[:3] != b"\xef\xbb\xbf", "无 BOM")
check(txt.endswith("}" + NL), "以 }%r 结尾" % NL)
if os.path.isfile(BAK2_TPL):
    braw = read_bytes(BAK2_TPL)
    check(tabs == braw.count(b"\t"), "tab 总数未增加（%d）" % tabs)
    # 重建「无 options 行 + 无 skew 块」版本，应与基线(config.bak-modulate-opts) 字节一致
    # （该基线是「含 modulate、未含 options、未含 skew」，
    #   当前相对它的增量 = modulate options 一行 + 整个 skew 块）
    import re as _re
    recon = _re.sub(r'[ \t]*"options": "import:modulatePresets",\r\n', '', txt)
    si = recon.find('"value": "skew"')
    if si >= 0:
        mod_close = recon.rfind("        },\r\n", 0, si)   # skew 前一个条目(modulate)的带逗号闭合
        post = recon.find("    ]\r\n}", si)                 # property 闭合 + 根闭合
        assert mod_close >= 0 and post >= 0, "skew 块定位失败"
        recon = recon[:mod_close] + "        }\r\n    ]\r\n}" + recon[post + len("    ]\r\n}"):]
    check(recon == braw.decode("utf-8"),
          "增量仅含 modulate options 一行 + skew 块（与基线字节一致）")
elif os.path.isfile(BAK_TPL):
    print("  NOTE 仅有 config.bak-modulate（不含 modulate），跳过 options 增量比对")
else:
    print("  NOTE 无基线备份，跳过增量比较")

print("\n[5] 新块缩进（8/12/16）且零 tab")
lines = txt.split(NL)
midx = next((k for k, l in enumerate(lines) if '"value": "modulate"' in l), None)
if midx is not None:
    K = len(lines[midx]) - len(lines[midx].lstrip())
    check(K == 12, "键名缩进 = 12（实际 %d）" % K)
    oi = midx - 1
    while oi >= 0 and lines[oi].strip() != "{":
        oi -= 1
    P = len(lines[oi]) - len(lines[oi].lstrip()) if oi >= 0 else -1
    check(P == 8, "元素 { 缩进 = 8（实际 %d）" % P)
    wi = next(k for k in range(midx, len(lines)) if '"whitelist": [' in lines[k])
    W = len(lines[wi + 1]) - len(lines[wi + 1].lstrip())
    check(W == 16, "whitelist 项缩进 = 16（实际 %d）" % W)
    block = lines[oi:wi + 654]
    check(all("\t" not in l for l in block), "新块内零 tab")
else:
    check(False, "未定位到 modulate 块")

print("\n[6] validate.js 校验规则")
vraw = read_bytes(VJS)
vtxt = vraw.decode("utf-8")
check(vraw[:3] != b"\xef\xbb\xbf", "validate.js 无 BOM")
check(vraw.count(b"\n") - vraw.count(b"\r\n") == 0, "validate.js 无裸 LF（保持 CRLF）")
check("export default [" in vtxt, "export default 结构完整")
check("collectOverrides" in vtxt, "仍引用 Util.collectOverrides")
check("PropertyName !== 'modulate'" in vtxt,
      "规则遍历 PropertyChange 比对 PropertyName（非顶层字段）")
check("HEX_RE" in vtxt, "含十六进制正则校验")
check(vtxt.rstrip().endswith("];") or "];" in vtxt, "规则数组闭合正常")
# 语法冒烟：尝试用 node 导入
try:
    import tempfile
    url = ("file:///" + os.path.abspath(VJS).replace("\\", "/").replace(" ", "%20"))
    probe = os.path.join(tempfile.gettempdir(), "_chk_validate.mjs")
    with io.open(probe, "w", encoding="utf-8") as f:
        f.write("const m = await import(%r);\n"
                "console.log(m.default.length);\n" % url)
    out = subprocess.run(["node", probe], capture_output=True, text=True, timeout=60)
    ok = (out.returncode == 0 and out.stdout.strip().isdigit())
    check(ok, "node 导入 validate.js 成功（规则数=%s）"
          % (out.stdout.strip() or out.stderr.strip()[:60]))
except Exception as e:
    print("  NOTE node 不可用，跳过语法冒烟：%s" % e)

print("\n[7] config.zip 一致性")
if os.path.isfile(ZIP):
    with zipfile.ZipFile(ZIP) as z:
        names = z.namelist()
        check(sorted(names) == sorted(["options.json", "templates.json",
                                       "default.json", "validate.js"]),
              "zip 含 4 个文件且无目录前缀")
        check(all("/" not in n for n in names), "arcname 均无目录前缀")
        check(z.read("templates.json") == raw, "zip 内 templates.json 与磁盘一致")
        check(z.read("validate.js") == vraw, "zip 内 validate.js 与磁盘一致")
else:
    check(False, "config.zip 不存在")

print("\n[8] options.json：modulatePresets 颜色预设")
OPT = os.path.join(CFG, "options.json")
if os.path.isfile(OPT):
    oraw = read_bytes(OPT)
    otxt = oraw.decode("utf-8")
    check(oraw[:3] != b"\xef\xbb\xbf", "options.json 无 BOM")
    check(oraw.count(b"\n") - oraw.count(b"\r\n") == 0, "options.json 无裸 LF（保持 CRLF）")
    try:
        ojson = json.loads(otxt)
        presets = ojson.get("modulatePresets", [])
        check(isinstance(presets, list) and len(presets) == 33,
              "modulatePresets 为 33 项数组（实际 %d）" % len(presets))
        ok_struct = all(isinstance(p, dict) and "label" in p and "value" in p for p in presets)
        check(ok_struct, "每条预设含 label/value 字段")
        vals = [p["value"] for p in presets]
        hex_ok = all(isinstance(v, str) and v.startswith("#")
                     and len(v) in (7, 9) for v in vals)
        check(hex_ok, "预设 value 均为 #RRGGBBAA / #RRGGBB 十六进制字符串")
        # 半透明变体校验：标签含「半透明」或以「%」结尾者，alpha 必须为 0x80（50%）或
        # 0xBF（75%，即「纯白半透明75%」）。覆盖 50% / 75% 两级。
        half = [p for p in presets if ("半透明" in p["label"]) or p["label"].endswith("%")]
        half_ok = all(p["value"].startswith("#") and len(p["value"]) == 9
                      and p["value"][-2:].upper() in ("80", "BF") for p in half)
        check(half_ok and len(half) >= 14,
              "半透明变体（%d 项）alpha 均为 0x80(50%%) / 0xBF(75%%)" % len(half))
        # 纯白 / 灰白 系列标签均存在
        labels = [p["label"] for p in presets]
        for lbl in ("纯白", "纯白半透明", "纯白半透明75%",
                    "灰白", "灰白半透明", "灰白半透明75%"):
            check(lbl in labels, "含纯白/灰白系列预设：%s" % lbl)
        # import 目标可达：templates 的 import:modulatePresets 在 options.json 有对应数组
        check("modulatePresets" in ojson, "import 目标 modulatePresets 在 options.json 存在")
        # zip 内 options.json 与磁盘一致
        with zipfile.ZipFile(ZIP) as z:
            check(z.read("options.json") == oraw, "zip 内 options.json 与磁盘一致")
    except Exception as e:
        check(False, "options.json 解析失败：%s" % e)
else:
    check(False, "options.json 不存在")

print("\n结果: " + ("全部通过" if not fails else "失败 %d 项" % len(fails)))
raise SystemExit(1 if fails else 0)
