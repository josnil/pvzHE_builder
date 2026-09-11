# -*- coding: utf-8 -*-
"""verify_gap_fixes.py —— 离线校验缺口补齐结果"""
import io, os, sys, json, hashlib, zipfile, re

CFG = r"D:\zzz\自制+官方构建器\杂交版官方关卡构建器v0.27\关卡构建器\config"
GAME = r"D:\zzz\pvzHE\解包\植物大战僵尸杂交版"
GAP = r"D:\zzz\pvzHE\解包\植物大战僵尸杂交版\Asset\Anime\Character\Zombie\gap_candidates.json"

opt = json.load(io.open(os.path.join(CFG, "options.json"), encoding="utf-8"))
tpl = json.load(io.open(os.path.join(CFG, "templates.json"), encoding="utf-8"))
gap = json.load(io.open(GAP, encoding="utf-8"))
fails = []


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


# [1] options 键项数
print("[1] options.json 项数")
check(len(opt["mapFunction"]) == 13, f"mapFunction 13 项（{len(opt['mapFunction'])}）")
check(len(opt["finishMethod"]) == 6, f"finishMethod 6 项（{len(opt['finishMethod'])}）")
check(len(opt["collectable"]) == 18, f"collectable 18 项（{len(opt['collectable'])}）")
check(len(opt["armor"]) == 40, f"armor 40 项（{len(opt['armor'])}）")
check(len(opt["cardType"]) == 10, f"cardType 10 项（{len(opt['cardType'])}）")
check(len(opt["categoryName"]) == 10, f"categoryName 10 项（{len(opt['categoryName'])}）")

# [2] cardType/categoryName 修正确
print("[2] cardType/categoryName 修正")
ct_vals = {e["value"] for e in opt["cardType"]}
check("OriginalP" not in ct_vals, "cardType 无 OriginalP")
check("Original" in ct_vals, "cardType 有 Original")
check("Noone" in ct_vals, "cardType 有 Noone")
cn_vals = {e["value"] for e in opt["categoryName"]}
check("OriginalP" not in cn_vals, "categoryName 无 OriginalP")
check("Original" in cn_vals, "categoryName 有 Original")
check("Noone" in cn_vals, "categoryName 有 Noone")

# [3] 与游戏枚举一致
print("[3] 与游戏枚举一致")
fm_vals = {e["value"].lower() for e in opt["finishMethod"]}
check(fm_vals == {"wave", "vase", "izm", "quiz", "izm2", "empty"}, "finishMethod 与 LEVEL_FINISH_METHOD 一致")
rw_vals = {e["value"].lower() for e in tpl["reward"]}
check(rw_vals == {"noone", "packet", "collectable", "coin", "trophy"}, "reward 与 LEVEL_REWARDTYPE 一致")
ct_vals_lower = {e["value"].lower() for e in opt["cardType"]}
check(ct_vals_lower == {"noone", "white", "gold", "diamond", "colour", "star", "original", "zombie", "cover", "gray"},
      "cardType 与 PACKET_TYPE 一致")
mf_vals = {e["value"] for e in opt["mapFunction"]}
for fn in ["ShowShovel", "BackShovel", "ShowGlove", "BackGlove", "CharacterClear", "LineUseSet", "ShowRow5"]:
    check(fn in mf_vals, f"mapFunction 含 {fn}")
cl_vals = {e["value"] for e in opt["collectable"]}
for c in ["Chapter7Paper", "ShovelSkeleton", "Chapter8Paper", "ShovelExplode", "Chapter9Paper"]:
    check(c in cl_vals, f"collectable 含 {c}")
ar_vals = {e["value"] for e in opt["armor"]}
for a in ["PogoBall", "JackGenebox", "HelmetNano", "BossDaveDoomShield"]:
    check(a in ar_vals, f"armor 含 {a}")
# armor 新项有 slot + whitelist
for a in opt["armor"]:
    if a["value"] in ("PogoBall", "JackGenebox", "HelmetNano", "BossDaveDoomShield"):
        check("slot" in a and "whitelist" in a, f"armor {a['value']} 有 slot+whitelist")
        check(len(a.get("whitelist", [])) == 570, f"armor {a['value']} whitelist=570")

# [4] property 71 项 whitelist 命中
print("[4] property whitelist 71 项命中")
# 用第一个匹配的 property 条目（fireNum/restTime 有重复条目，去重保留首条）
prop_map = {}
for p in tpl["property"]:
    if p["value"] not in prop_map:
        prop_map[p["value"]] = p
missing_hit = 0
for r in gap["A_missing_whitelist"]:
    p = prop_map.get(r["prop"])
    if not p:
        fails.append(f"property {r['prop']} not found")
        missing_hit += 1
        continue
    wl = p.get("whitelist", [])
    if r["id"] not in wl:
        fails.append(f"{r['id']} not in {r['prop']} whitelist")
        missing_hit += 1
check(missing_hit == 0, f"71 项全部命中（缺 {missing_hit}）")

# [5] event[5] Row->Column
print("[5] event[5] Row->Column")
warn_ev = [e for e in tpl["event"] if e.get("value") == "CurrentMapUseWarningLine"]
if warn_ev:
    props = warn_ev[0].get("properties", [])
    has_column = any(p.get("value") == "Column" for p in props)
    has_row = any(p.get("value") == "Row" for p in props)
    check(has_column, "event[5] 用 Column")
    check(not has_row, "event[5] 不再用 Row")

# [6] reward +Trophy
print("[6] reward +Trophy")
check(any(e["value"] == "Trophy" for e in tpl["reward"]), "reward 含 Trophy")

# [7] validate.js +EventEntry
print("[7] validate.js +EventEntry")
vj = open(os.path.join(CFG, "validate.js"), encoding="utf-8").read()
check("EventEntry" in vj, "validate.js 含 EventEntry")

# [8] JSON 合法性 + CRLF + BOM
print("[8] 编码/换行")
for n in ["options.json", "templates.json", "validate.js"]:
    raw = open(os.path.join(CFG, n), "rb").read()
    check(raw[:3] != b"\xef\xbb\xbf", f"{n} 无 BOM")
    check(raw.count(b"\n") == raw.count(b"\r\n"), f"{n} 统一 CRLF")

# [9] zip md5 一致
print("[9] config.zip md5 一致")
z = zipfile.ZipFile(os.path.join(CFG, "config.zip"))
check(sorted(z.namelist()) == ["default.json", "options.json", "templates.json", "validate.js"], "zip 4 条目")
for n in z.namelist():
    d = hashlib.md5(z.read(n)).hexdigest()
    f = hashlib.md5(open(os.path.join(CFG, n), "rb").read()).hexdigest()
    check(d == f, f"md5 一致: {n}")

# [10] 存量未受影响
print("[10] 存量未受影响")
check(len(tpl["property"]) == 44, f"property 仍 44 条（{len(tpl['property'])}）")
check(len(tpl["event"]) == 36, f"event 仍 36 条（{len(tpl['event'])}）")
check(len(tpl["attribute"]) == 25, f"attribute 仍 25 条（{len(tpl['attribute'])}）")
# cardType 既有 8 项（除 Noone）label 未变
old_ct = {("白卡", "White"), ("紫卡", "Cover"), ("金卡", "Gold"), ("钻卡", "Diamond"),
           ("彩卡", "Colour"), ("星卡", "Star"), ("原卡", "Original"), ("僵尸卡", "Zombie"), ("模仿卡", "Gray")}
cur_ct = {(e["label"], e["value"]) for e in opt["cardType"] if e["value"] != "Noone"}
check(old_ct == cur_ct, "cardType 既有 9 项 label 未变（OriginalP→Original）")

print("\n结果: " + ("全部通过" if not fails else f"失败 {len(fails)} 项"))
sys.exit(1 if fails else 0)
