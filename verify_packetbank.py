# -*- coding: utf-8 -*-
"""verify_packetbank.py
复现构建器前端的 uh() / wa() / ba() / ka() 逻辑，离线校验本次 packetBank 改造。
不启动 exe。全部 OK 且退出码 0 才算通过。
"""
import io, os, sys, json, hashlib, zipfile

CFG = r"D:\zzz\自制+官方构建器\杂交版官方关卡构建器v0.27\关卡构建器\config"
GAME = r"D:\zzz\pvzHE\解包\植物大战僵尸杂交版\Asset\Config\PacketBank\PacketBankResource.json"


def load(p):
    return json.load(io.open(p, encoding="utf-8"))


opt = load(os.path.join(CFG, "options.json"))
tpl = load(os.path.join(CFG, "templates.json"))

fails = []


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


# ---------- 复现前端 uh()：import:a,b,c 解析 ----------
def uh(spec):
    if not isinstance(spec, str) or not spec.startswith("import:"):
        return None
    out = []
    for k in spec[len("import:"):].split(","):
        v = opt.get(k)
        if not isinstance(v, list):      # 键不存在或非数组 -> 与前端一致返回 null
            return None
        out.extend(v)
    return out


# ---------- 复现前端 wa() / ba() / ka() ----------
def wa(class_type):
    return "character" if class_type in ("zombie", "plant", "other", "ball") else "card"


def ba(character_type):
    out = []
    for p in tpl["property"]:
        wl, bl = p.get("whitelist"), p.get("blacklist")
        if wl is not None and character_type not in wl:
            continue
        if bl is not None and character_type in bl:
            continue
        out.append({"label": p["label"], "value": "$" + p["value"], "property": p})
    return out


def ka(class_type, character_type):
    items = [a for a in tpl["attribute"] if class_type in a.get("class", [])]
    if wa(class_type) == "character":
        items = items + ba(character_type)
    seen, ded = set(), []
    for it in items:
        v = it.get("value")
        if not v or v in seen:
            continue
        seen.add(v)
        ded.append(it)
    return ded


print("[1] options.packetBankAll 完整性")
opts = uh("import:packetBankAll")
check(opts is not None, "import:packetBankAll 可解析（是数组型顶层键）")
check(len(opts) == 22, "共 22 项（实际 %s）" % (len(opts) if opts else 0))
if opts:
    vals = [o["value"] for o in opts]
    check(len(set(vals)) == len(vals), "无重复 value")
    check(all(set(o) <= {"label", "value"} for o in opts), "每项只含 label/value")
    check(all(isinstance(o.get("label"), str) and o["label"] for o in opts), "label 均非空")
    banks = set(load(GAME).keys())
    check({v.lower() for v in vals} == {b.lower() for b in banks},
          "22 项与 PacketBankResource.json 键名一致（忽略大小写）")
    check(len(banks) == 22, "游戏卡池表本身是 22 个（实际 %d）" % len(banks))

print("[2] templates.property 新增条目")
pb = [p for p in tpl["property"] if p["value"] == "packetBank"]
check(len(pb) == 1, "property 中 packetBank 唯一（实际 %d 条）" % len(pb))
if pb:
    p = pb[0]
    check(p.get("type") == "select", "type == select")
    check(uh(p.get("options")) is not None, "options 可解析: %s" % p.get("options"))
    check(len(uh(p.get("options")) or []) == 22, "下拉共 22 项")
    check(p.get("whitelist") == ["ZombieNormalPresentBox", "ZombieImpPresentBox",
                                 "ZombieGargantuarPresentBox", "PlantPresentBox"],
          "whitelist 精确等于 4 个礼盒 ID")

print("[3] 面板注入（ka + 去重）")
for cid in ["ZombieNormalPresentBox", "ZombieImpPresentBox",
            "ZombieGargantuarPresentBox", "PlantPresentBox"]:
    ct = "zombie" if cid.startswith("Zombie") else "plant"
    hit = [x for x in ka(ct, cid) if x["value"] == "$packetBank"]
    check(len(hit) == 1, "%s(%s) 面板出现且仅出现一次 packetBank" % (cid, ct))

print("[4] 不该出现的单位")
for cid, ct in [("ZombieNormal", "zombie"), ("PlantPeaShooterSingle", "plant"),
                ("PlantPresentBoxGreen", "plant"), ("ZombieGargantuar", "zombie")]:
    hit = [x for x in ka(ct, cid) if x["value"] == "$packetBank"]
    check(len(hit) == 0, "%s 不出现 packetBank" % cid)

print("[5] 存量不受影响")
check(len(tpl["property"]) == 44, "property 44 条（实际 %d）" % len(tpl["property"]))
check("packetBank" in opt and len(opt["packetBank"]) == 4, "既有 options.packetBank 仍为 4 项")
check(uh("import:plant,zombie,zombieExtra,item") is not None, "存量 import 仍可解析")
check(uh("import:plant,zombie,zombieExtra,other") is None, "既有坏引用 'other' 仍为 null（未恶化）")
check(len(tpl["attribute"]) == 25 and len(tpl["event"]) == 36,
      "attribute/event 条目数未变（%d / %d）" % (len(tpl["attribute"]), len(tpl["event"])))

print("[5b] options.packetBankType 补齐结果")
pbt = opt["packetBankType"]
banks = set(load(GAME).keys())
check(len(pbt) == 22, "packetBankType 22 项（实际 %d）" % len(pbt))
old9 = ["GeneralPlant", "GeneralPlantNoSun", "GeneralPlantNoLeaf", "GeneralZombie",
        "TotalZombie", "OriginalPlant", "OriginalZombie", "Original", "Total"]
check([o["value"] for o in pbt[:9]] == old9, "既有 9 项的顺序与取值完全未变")
check([o["label"] for o in pbt[:9]] == ["植物卡牌", "无阳光植物", "无保护伞植物", "僵尸卡牌",
                                        "全部僵尸卡牌", "原版植物卡牌", "原版僵尸卡牌",
                                        "全部原版卡牌", "全部卡牌"], "既有 9 项的 label 未变")
check({o["value"].lower() for o in pbt} == {b.lower() for b in banks},
      "packetBankType 22 项与 PacketBankResource.json 键名一致（忽略大小写）")
check({o["value"].lower() for o in uh("import:packetBankAll")} ==
      {o["value"].lower() for o in pbt},
      "packetBankAll 与 packetBankType 的取值集合一致（label 风格不同是刻意的）")

print("[6] JSON 编码/换行未破坏")
for n in ["options.json", "templates.json"]:
    raw = open(os.path.join(CFG, n), "rb").read()
    check(raw[:3] != b"\xef\xbb\xbf", "%s 无 BOM" % n)
    check(raw.endswith(b"}\r\n"), "%s 仍以 }\\r\\n 结尾" % n)
    check(raw.count(b"\n") == raw.count(b"\r\n"), "%s 全文件统一 CRLF（无裸 LF）" % n)

keys = list(opt.keys())
check(keys.index("packetBankAll") == keys.index("packetBank") + 1,
      "packetBankAll 紧随 packetBank 之后（键顺序正确）")
check("packetBankAll" not in tpl and "packetBankAll" in opt,
      "packetBankAll 定义在 options.json（而非 templates.json）")

print("[7] config.zip 与目录逐文件 md5 一致")
z = zipfile.ZipFile(os.path.join(CFG, "config.zip"))
check(sorted(z.namelist()) == ["default.json", "options.json", "templates.json", "validate.js"],
      "zip 内 4 条目、无目录前缀")
for n in sorted(z.namelist()):
    d = hashlib.md5(z.read(n)).hexdigest()
    f = hashlib.md5(open(os.path.join(CFG, n), "rb").read()).hexdigest()
    check(d == f, "md5 一致: %s (%s)" % (n, d))

print("\n结果: " + ("全部通过" if not fails else "失败 %d 项" % len(fails)))
sys.exit(1 if fails else 0)
