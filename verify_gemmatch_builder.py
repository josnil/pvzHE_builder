# -*- coding: utf-8 -*-
"""verify_gemmatch_builder.py
「全模式关卡构建器」离线校验：确认 gemmatch_builder.html 与 build_gemmatch_builder.py
处于一致的最新状态。全部检查只读（重跑生成是幂等的，用于确认确定性）。

检查项：
  1. 重跑生成的确定性（md5 前后一致）
  2. DATA 与官方构建器 config/ 同源：property=44（含 modulate/skew/swayAmplitude/modulateCycle）、attribute=25、event=36
  2b. 预设数据源（需求 3/4/5/6/7/9）：packetBankType=22 / categoryName=11 / mowerItems=3 /
      featureLabels=27 / talkModes 含 Tutorial
  3. modulatePresets 预设已进 DATA（染色下拉可用）
  4. 全模式数据：featureNames=27（含 Glove/RainMode/ConveyorBelt）、processNames=6
  5. Feature/Process 字段规格表完整（25 个 Feature schema + 6 个 Process schema）
  6. RainMode/ConveyorBelt 的关键 JSON 键正确（Type/AliveTime/Interval/Packet、
     Interval/IntervalIncreaseEvery/IntervalMagnification/MaxPacketCount/PacketPrioritySpawnList/WaveEvent）
  7. 往返无损与调试钩子标记存在（RAWFLAGS / __builder_dbg / dataRawFallback）
  8. 主脚本 JS 语法检查（有 node 时）
  9. 备份文件存在
"""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(BASE, "gemmatch_builder.html")
GEN = os.path.join(BASE, "build_gemmatch_builder.py")

PASS, FAIL = [], []


def ck(name, cond, detail=""):
    (PASS if cond else FAIL).append(name + (("  <- " + detail) if detail and not cond else ""))


def md5(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def load_data():
    html = io.open(HTML, encoding="utf-8").read()
    m = re.search(r'<script id="DATA" type="application/json">([\s\S]*?)</script>', html)
    assert m, "DATA script 未找到"
    return html, json.loads(m.group(1).replace("<\\/", "</"))


def main():
    # 1. 生成确定性
    h1 = md5(HTML)
    subprocess.run([sys.executable, GEN], cwd=BASE, check=True,
                   stdout=subprocess.DEVNULL)
    ck("重跑生成确定性（md5 一致）", md5(HTML) == h1)

    html, data = load_data()

    # 2. 与官方构建器同源
    ck("property=44（与官方 templates.json 一致，含 modulate/skew/swayAmplitude/modulateCycle）",
       len(data.get("property", [])) == 44, str(len(data.get("property", []))))
    pvals = [p["value"] for p in data["property"]]
    ck("property 含 modulate", "modulate" in pvals)
    ck("property 含 skew", "skew" in pvals)
    ck("property 含 swayAmplitude", "swayAmplitude" in pvals)
    ck("property 含 modulateCycle", "modulateCycle" in pvals)
    ck("attribute=25", len(data.get("attribute", [])) == 25)
    ck("event=36", len(data.get("event", [])) == 36)

    # 2b. 预设数据源（需求 3/4/5/6/7/9）
    ck("packetBankType=22（卡池类型预设）", len(data.get("packetBankType", [])) == 22,
       str(len(data.get("packetBankType", []))))
    ck("categoryName=11（品质范围预设）", len(data.get("categoryName", [])) == 11,
       str(len(data.get("categoryName", []))))
    ck("mowerItems=3（小推车道具预设）", len(data.get("mowerItems", [])) == 3,
       str(len(data.get("mowerItems", []))))
    ck("featureLabels=27（Feature 中文名）", len(data.get("featureLabels", {})) == 27,
       str(len(data.get("featureLabels", {}))))
    ck("talkModes 含 Tutorial", any(m.get("value") == "Tutorial"
                                     for m in data.get("talkModes", [])))

    # 2b. Arg 预设 / 铲子预设（本轮新增）
    tap = data.get("talkArgPresets", [])
    ck("talkArgPresets > 300（植物+僵尸+item+talkArgOther）", len(tap) > 300, str(len(tap)))
    ck("talkArgPresets 每项含 label+value 且 value 唯一",
       all(x.get("label") and x.get("value") for x in tap)
       and len(set(x["value"] for x in tap)) == len(tap))
    shv = data.get("shovels", [])
    ck("shovels=11（铲子预设）", len(shv) == 11, str(len(shv)))
    ck("shovels label 全为中文",
       all(re.search(r"[\u4e00-\u9fff]", x["label"]) for x in shv),
       str([x["label"] for x in shv]))
    ck("shovels 含 ShovelDefault=铁铲",
       any(x["value"] == "ShovelDefault" and x["label"] == "铁铲" for x in shv))
    ck("collectable 已进 DATA（Reward 用）", len(data.get("collectable", [])) >= 11,
       str(len(data.get("collectable", []))))

    # 3. 染色预设
    mp = data.get("modulatePresets", [])
    ck("modulatePresets 已进 DATA（>=11 项）", len(mp) >= 11, str(len(mp)))
    ck("modulatePresets 值为 #RRGGBBAA 形式",
       all(re.fullmatch(r"#[0-9A-Fa-f]{8}|#[0-9A-Fa-f]{6}", x["value"]) for x in mp))

    # 4. 全模式数据
    fn = data.get("featureNames", [])
    ck("featureNames=27", len(fn) == 27, str(len(fn)))
    for n in ("Glove", "RainMode", "ConveyorBelt", "SlotMachine", "Fog", "ScreenEffect"):
        ck("featureNames 含 " + n, n in fn)
    ck("processNames=6", data.get("processNames") == ["Wave", "Vase", "IZM", "IZM2", "Quiz", "Empty"])

    # 5. schema 表
    fs_ = data.get("featureSchemas", {})
    ps_ = data.get("processSchemas", {})
    ck("featureSchemas=25（27 减去 Wave/GemMatch 两个专用编辑器）",
       len(fs_) == 25, str(len(fs_)))
    ck("processSchemas=6", len(ps_) == 6, str(len(ps_)))
    ck("waveSimpleFields=11", len(data.get("waveSimpleFields", [])) == 11)
    ck("gmFields=19", len(data.get("gmFields", [])) == 19)

    # 6. RainMode / ConveyorBelt 关键键
    def keys_of(schema):
        return [f["k"] for f in fs_.get(schema, [])]
    ck("RainMode 键 = Type/AliveTime/Interval/Packet",
       keys_of("RainMode") == ["Type", "AliveTime", "Interval", "Packet"], str(keys_of("RainMode")))
    ck("ConveyorBelt 键完整",
       set(["Type", "Interval", "IntervalIncreaseEvery", "IntervalMagnification",
            "MaxPacketCount", "Packet", "PacketPrioritySpawnList", "WaveEvent"])
       <= set(keys_of("ConveyorBelt")), str(keys_of("ConveyorBelt")))
    ck("Vase(过程) 含 Vase/VaseFill",
       {"Vase", "VaseFill"} <= set(f["k"] for f in ps_.get("Vase", [])))
    ck("Quiz(过程) 13 字段", len(ps_.get("Quiz", [])) == 13)

    # 6b. Shovel schema（本轮新增）
    ck("Shovel schema 含 ShovelName",
       "ShovelName" in keys_of("Shovel"), str(keys_of("Shovel")))
    ck("Shovel.ShovelName 为 combo + imp=shovels",
       any(f["k"] == "ShovelName" and f.get("t") == "combo"
           and f.get("imp") == "shovels" and f.get("tip") for f in fs_.get("Shovel", [])))

    # 6c. 枚举中文化（本轮新增：BGM/Mower/Brain 走 labelCombo；Progress/Sun/SeedBank 走 opts 对象）
    ck("processLabels=6 且全中文",
       len(data.get("processLabels", {})) == 6
       and all(re.search(r"[\u4e00-\u9fff]", v) for v in data.get("processLabels", {}).values()),
       str(data.get("processLabels")))
    ck("processLabels 覆盖全部 processNames",
       set(data.get("processLabels", {})) == set(data.get("processNames", [])))

    def opts_of(schema, key):
        for f in fs_.get(schema, []):
            if f["k"] == key:
                return f.get("opts")
        return None

    def all_zh(opts):
        """opts 必须是对象数组，且每项 label 含中文、value 非空"""
        if not isinstance(opts, list) or not opts:
            return False
        for o in opts:
            if not isinstance(o, dict) or not o.get("value"):
                return False
            if not re.search(r"[\u4e00-\u9fff]", str(o.get("label", ""))):
                return False
        return True

    for schema, key in (("Sun", "MovingMethod"), ("Progress", "Mode"), ("SeedBank", "Method"),
                        ("RainMode", "Type")):
        ck("%s.%s opts 为中文对象数组" % (schema, key), all_zh(opts_of(schema, key)),
           str(opts_of(schema, key)))
    for key in ("DifficultyVisibility", "LevelNameVisibility", "SurvivalVisibility",
                "ProgressVisibility", "ProgressTextVisibility"):
        ck("Progress.%s opts 为中文对象数组" % key, all_zh(opts_of("Progress", key)),
           str(opts_of("Progress", key)))
    ck("Progress 5 个可见性 opts 含 Show/Hide 值",
       all({o["value"] for o in (opts_of("Progress", k) or [])} == {"Auto", "Show", "Hide"}
           for k in ("DifficultyVisibility", "LevelNameVisibility", "SurvivalVisibility",
                     "ProgressVisibility", "ProgressTextVisibility")))
    # combo 型字段（需中文预设）
    for schema, key in (("BGM", "BGMName"), ("Mower", "MowerPacketName"),
                        ("Mower", "WaterMowerPacketName"), ("Mower", "TargetZombiePacketName"),
                        ("Mower", "PreviewSpriteName"), ("Brain", "PacketName"),
                        ("NpcTalk", "TemporaryBGM")):
        ck("%s.%s 为 combo（labelCombo 显示中文）" % (schema, key),
           any(f["k"] == key and f.get("t") == "combo" and f.get("imp")
               for f in fs_.get(schema, [])), str(opts_of(schema, key)))

    # 7. 往返无损 / 调试钩子标记
    for marker in ("RAWFLAGS", "__builder_dbg", "dataRawFallback", "featureManager",
                   "processEditor", "packetWeightEditor", "prioEditor", "prespawnEditor",
                   "vaseEditor", "vaseFillEditor",
                   "labelCombo", "propChecklist", "cardOverrideFields", "packetOverrideEditor",
                   "talkEditor", "tutorialEditor", "taInput", "showSaveFilePicker",
                   "argListEditor", "rewardEditor",
                   "normOpts", "stackBlock"):
        ck("HTML 含标记 " + marker, marker in html)
    ck("CSS 含 .stack 全宽纵向块（嵌套覆盖用）", ".stack{" in html and ".stackbody{" in html)
    ck("旧 presetCombo 死代码已移除（统一走 labelCombo）", "function presetCombo" not in html)

    # 7b. PropertyChange 惰性初始化（防「空数组被 delete 后 push 崩溃」回归）
    #     renderPC() 末尾 `if(!obj.PropertyChange.length) delete obj.PropertyChange;` 保证导出干净，
    #     代价是「添加」型 handler 必须先用 ensurePC() 重建数组。
    ck("overrideEditor 含 ensurePC() 惰性初始化", "function ensurePC()" in html)
    naked = re.findall(r"obj\.PropertyChange\.push\(", html)
    ck("不存在裸 obj.PropertyChange.push（必须走 ensurePC()）", len(naked) == 0,
       "裸调用 %d 处" % len(naked))
    ck("三条添加路径均走 ensurePC()",
       html.count("ensurePC()") >= 3, "ensurePC() 出现 %d 次" % html.count("ensurePC()"))
    ck("回归脚本 verify_pc_regression.js 存在",
       os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "verify_pc_regression.js")))

    # 8. JS 语法（有 node 时）
    node = shutil.which("node")
    if node:
        import tempfile
        scripts = re.findall(r"<script(?:\s[^>]*)?>([\s\S]*?)</script>", html)
        main_js = scripts[-1] if scripts else ""
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                         encoding="utf-8") as tf:
            tf.write(main_js)
            tmp = tf.name
        try:
            r = subprocess.run(
                [node, "-e",
                 "new Function(require('fs').readFileSync(process.argv[1],'utf8'));"
                 " console.log('OK')", tmp],
                capture_output=True, text=True)
            ck("主脚本 JS 语法（node new Function）", r.returncode == 0 and "OK" in r.stdout,
               r.stderr.strip()[:200])
        finally:
            os.unlink(tmp)
    else:
        PASS.append("JS 语法检查跳过（无 node）")

    # 9. 备份
    for bak in ("build_gemmatch_builder.py.bak-fullmode-20260906",
                "gemmatch_builder.html.bak-fullmode-20260906"):
        ck("备份存在 " + bak, os.path.isfile(os.path.join(BASE, bak)))

    print("=" * 60)
    for p in PASS:
        print("[PASS]", p)
    for f in FAIL:
        print("[FAIL]", f)
    print("=" * 60)
    print("通过 %d 项 / 失败 %d 项" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
