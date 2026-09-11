# -*- coding: utf-8 -*-
"""build_gemmatch_builder.py
生成「全模式关卡构建器」——单文件 HTML，浏览器直接打开即可用。

数据源全部来自官方构建器 config/ 与 gen_gemmatch_level.py，保证与官方构建器同源：
  - options.json    : plant / zombie / zombieExtra / item / armor / projectile / map / bgm /
                      produceType / cardType / packetBankAll / modulatePresets / sunType /
                      packetBankType / categoryName / talkNpc / talkAudio / talkAnime / talkArg
                      / talkArgOther / talkMode（+ 派生 mowerItems）
  - templates.json  : property(44) / attribute(25) / classTypeComputed
  - gemmatch_template.json    : 内置默认模板
  - gen_gemmatch_level.py     : GEMMATCH_FIELDS(19)（FEATURE_ORDER 改为本地定义）

支持全部 27 种 Feature（含 Glove / RainMode / ConveyorBelt）与 6 种 Process 游戏模式
（Wave / Vase / IZM / IZM2 / Quiz / Empty），导入导出往返无损。

UI 增强（2026-09-10）：Feature 名中文；属性覆盖勾选批量加入；BGM/Brain/Mower/NpcTalk/
ScreenEffect 预设；事件「生成卡牌/创建角色卡牌」属性覆盖可视化；RainMode/ConveyorBelt
每卡可编辑覆盖（品质/价格/涨价/格数/直接种植/角色覆盖）；NpcTalk 自定义对话与 Tutorial
自定义教程的嵌套编辑器。

产出: gemmatch_builder.html（零依赖、纯前端、无需服务器/联网）
"""
import io
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(BASE, "config")
sys.path.insert(0, BASE)

# 单一数据源：GemMatch 字段规格直接复用既有生成脚本
# （FEATURE_ORDER 不再从 gen_gemmatch_level.py 导入——全模式版需要 27 个 Feature，
#   为不动自制脚本 gen_gemmatch_level.py，在此本地定义）
from gen_gemmatch_level import GEMMATCH_FIELDS  # noqa: E402

# 新建关卡时 Feature 的默认顺序（与官方 MiniGames_Level5_1 一致的 9 段基线）
FEATURE_ORDER = ["Wave", "Map", "BGM", "Camera", "Progress", "PacketPick",
                 "SeedBank", "Sun", "GemMatch"]

# 游戏注册的全部 Feature 名（Registry/Battle/TowerDefenseBattleRegistry.cs:29-65 顺序）
FEATURE_NAMES = ["Camera", "Map", "Shovel", "Glove", "PacketPick", "Mower", "Brain",
                 "NpcTalk", "Sun", "Progress", "RainMode", "ConveyorBelt", "PacketBank",
                 "SeedBank", "PreSpawn", "BGM", "Fog", "LookStar", "ScreenEffect",
                 "WarningLine", "Portal", "Tutorial", "Event", "Hammer", "GemMatch",
                 "SlotMachine", "Wave"]

# Feature 中文名（UI 标题与下拉用；键与 FEATURE_NAMES 一一对应）
FEATURE_LABELS = {
    "Camera": "相机", "Map": "地图", "Shovel": "铲子", "Glove": "手套",
    "PacketPick": "选卡", "Mower": "小推车", "Brain": "脑子", "NpcTalk": "对话",
    "Sun": "阳光", "Progress": "进度", "RainMode": "阳光雨", "ConveyorBelt": "传送带",
    "PacketBank": "卡池", "SeedBank": "种子栏", "PreSpawn": "预种植", "BGM": "背景音乐",
    "Fog": "迷雾", "LookStar": "星光", "ScreenEffect": "屏幕特效", "WarningLine": "警戒线",
    "Portal": "传送门", "Tutorial": "教程", "Event": "事件", "Hammer": "锤子",
    "GemMatch": "宝石迷阵", "SlotMachine": "老虎机", "Wave": "波次",
}

# 游戏注册的全部 Process 名（同文件 :58-63，与 LEVEL_FINISH_METHOD 一一对应）
PROCESS_NAMES = ["Wave", "Vase", "IZM", "IZM2", "Quiz", "Empty"]

# Process 中文名（UI 下拉用；FinishMethod 枚举 = WAVE/VASE/IZM/QUIZ/IZM2/EMPTY）
PROCESS_LABELS = {
    "Wave": "波次模式",
    "Vase": "花瓶模式",
    "IZM": "我是僵尸 IZM",
    "IZM2": "我是僵尸 2 IZM2",
    "Quiz": "答题模式",
    "Empty": "空过程",
}


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def slim(entries):
    """只保留 label/value，去掉 uid/tags/wavePointCost 等构建器内部元数据以压缩体积。"""
    out = []
    for e in entries or []:
        if isinstance(e, dict):
            out.append({"label": e.get("label", e.get("value", "")), "value": e.get("value", "")})
        else:
            out.append({"label": str(e), "value": str(e)})
    return out


opt = load(os.path.join(CFG, "options.json"))
tpl = json.loads(io.open(os.path.join(CFG, "templates.json"), encoding="utf-8").read())
level_tmpl = load(os.path.join(BASE, "gemmatch_template.json"))

# ball 类 = item 中带 ball 标签的项（对应 templates.classTypeComputed 的 item[ball]）
ball_list = slim([i for i in opt.get("item", []) if "ball" in (i.get("tags") or [])])

# armor: 44 个防具只有 2 种不同 whitelist（570/571 项）→ 去重共享，避免体积膨胀
_armor_wls = []
armor_out = []
for a in opt.get("armor", []):
    wl = a.get("whitelist", [])
    idx = None
    for i, w in enumerate(_armor_wls):
        if w == wl:
            idx = i
            break
    if idx is None:
        _armor_wls.append(wl)
        idx = len(_armor_wls) - 1
    armor_out.append({"label": a.get("label", ""), "value": a.get("value", ""),
                      "slot": a.get("slot"), "wl": idx})

# property: 保留过滤与渲染所需的键（whitelist 是 ba() 过滤依据，必须保留）
prop_out = []
for p in tpl.get("property", []):
    item = {"label": p.get("label", ""), "value": p.get("value", ""), "type": p.get("type", "")}
    if p.get("unit"):
        item["unit"] = p["unit"]
    if p.get("options"):
        item["options"] = p["options"]
    if p.get("helpTip"):
        item["helpTip"] = p["helpTip"]
    item["whitelist"] = p.get("whitelist", [])
    prop_out.append(item)

# 派生数组（务必在 slim() 丢字段前）：
# 小推车相关道具（item 中 mower=true）——供 Mower 各卡牌/预览贴图预设
mower_items = slim([i for i in opt.get("item", []) if isinstance(i, dict) and i.get("mower")])
# 卡牌覆盖字段（attribute 中 class 含 *Card 的项）——供 TowerDefensePacketOverride 编辑器
card_attrs = [a for a in tpl.get("attribute", [])
              if any('Card' in c for c in (a.get("class") or []))]
# 硬编码枚举（游戏侧无 options 数组）
SCREEN_EFFECT_METHODS = [["无 NOONE", 0], ["选卡 CHOOSE", 1], ["预设 PRESET", 2],
                         ["传送带 CONVEYOR", 3], ["加雨 RAIN", 4]]
TUTORIAL_CONDITIONS = [
    {"name": "CheckCharacterNum", "label": "检查角色数量",
     "fields": [{"k": "CharacterName", "label": "角色名", "t": "combo", "imp": "zombie,zombieExtra"},
                {"k": "Method", "label": "比较", "t": "enum", "opts": [">", ">=", "==", "<", "<="]},
                {"k": "Num", "label": "数量", "t": "num"}]},
    {"name": "CheckSunCollect", "label": "检查阳光收集",
     "fields": [{"k": "Num", "label": "数量", "t": "num"}]},
]
# 对话模式（官方 options.talkMode 2 项 + 游戏侧 Tutorial 模式）
TALK_MODES = slim(opt.get("talkMode", [])) + [{"label": "教程", "value": "Tutorial"}]

# event: 36 条事件表（class=作用域 / value=EventName / display=显示模板 / properties=参数定义）
# 说明：事件 Value 是「具名键对象」而非数组（依据 TowerDefenseCharacterOverride.cs:102
#       GetValueOrDefault("Value", new Dictionary()).AsGodotDictionary()）
event_out = []
for e in tpl.get("event", []):
    props = []
    for pr in e.get("properties", []):
        spec = pr.get("property") or {}
        item = {"label": pr.get("label", pr.get("value", "")),
                "value": pr.get("value", ""),
                "type": spec.get("type", "text")}
        for k in ("default", "optional", "step", "min", "max",
                  "options", "classType", "characterRequires", "placeholder"):
            if k in spec:
                item[k] = spec[k]
        if spec.get("type") == "constant":
            item["constValue"] = spec.get("value")
        props.append(item)
    disp = e.get("display")
    event_out.append({
        "class": e.get("class", []),
        "label": e.get("label", ""),
        "value": e.get("value", ""),
        "display": disp.get("format", "") if isinstance(disp, dict) else (disp or ""),
        "properties": props,
    })

# GemMatch 字段规格（19 键，含 2 个派生默认值）
gm_fields = []
for name, spec in GEMMATCH_FIELDS.items():
    gm_fields.append({
        "name": name,
        "type": spec.get("type", "int"),
        "default": spec.get("default"),
        "label": spec.get("doc", name),
        "derived": name in ("matchValuePerMatch", "clearMatchCount"),
    })

# ---- Feature / Process 字段规格表 ----------------------------------------
# 字段出处（逐文件核对过源码，键名为 Init(data) 实际读取的 JSON 键）：
#   Glove            Registry\Battle\Feature\Glove\TowerDefenseBattleFeatureGlove.cs（无配置，Data={}）
#   RainMode         Resource\TowerDefense\Level\RainMode\TowerDefenseRainModeConfig.cs
#   ConveyorBelt     Resource\TowerDefense\Conveyor\TowerDefenseConveyorConfig.cs
#   ScreenEffect     Registry\Battle\Feature\ScreenEffect\TowerDefenseBattleFeatureScreenEffect.cs:27-50
#   SlotMachine      Registry\Battle\Feature\SlotMachine\TowerDefenseBattleFeatureSlotMachine.cs ReadConfig()
#   Fog              Resource\TowerDefense\Level\Fog\TowerDefenseLevelFogManagerConfig.cs
#   PreSpawn         Registry\Battle\Feature\PreSpawn\Resource\TowerDefenseBattleFeaturePreSpawnConfig.cs
#   PacketPick       Registry\Battle\Feature\PacketPick\Resource\TowerDefenseBattleFeaturePacketPickConfig.cs
#   Mower/Brain      各自 Resource\*Config.cs
#   Progress         Registry\Battle\Feature\Progress\Resource\TowerDefenseBattleFeatureProgressConfig.cs
#   Wave             Resource\TowerDefense\Level\Wave\TowerDefenseLevelWaveManagerConfig.cs
#   Event            Registry\Battle\Feature\Event\TowerDefenseBattleFeatureEvent.cs:50-54
#   NpcTalk/Tutorial/Portal/LookStar 等：小字段或运行态，raw 兜底
#   Vase(过程)       Registry\Battle\Process\Vase\Resource\TowerDefenseLevelVaseManagerConfig.cs
#   Quiz(过程)       Registry\Battle\Process\Quiz\Resource\TowerDefenseBattleProcessQuizConfig.cs
#   IZM(过程)        Resource\TowerDefense\Level\IZM\TowerDefenseLevelIZMManagerConfig.cs
#   Wave/IZM2(过程)  Registry\Battle\Process\Resource\TowerDefenseBattleProcessWaveEntryConfig.cs
# 字段类型: num=数字(留空不写) bool=开关 text=文本 sel=下拉(imp=DATA键/opts=枚举)
#           opts 支持 ["A","B"] 或 [{"label":"中文 A","value":"A"}] 两种写法（normOpts 归一化）
#           combo=预设下拉+自由输入（labelCombo，显示中文）；enumint=枚举→整数
#           plants=植物多选 pkts=权重掉落包 prio=优先发包 prespawn=预种植
#           vases=花瓶列表 vasefill=填瓶列表 slots=转盘卡池 rawkey=该键原始JSON

# 可见性三态（TowerDefenseProgressVisibility，Progress Feature 的 5 个 *Visibility 共用）
VIS_OPTS = [
    {"label": "自动 Auto（按模式默认）", "value": "Auto"},
    {"label": "显示 Show", "value": "Show"},
    {"label": "隐藏 Hide", "value": "Hide"},
]

FEATURE_SCHEMAS = {
    "Camera": [],
    "Map": [
        {"k": "MapName", "label": "地图", "t": "sel", "imp": "map", "req": True},
    ],
    "Shovel": [
        {"k": "ShovelName", "label": "自定义铲子", "t": "combo", "imp": "shovels",
         "tip": "⚠️ 游戏 TowerDefenseBattleFeatureShovel.Init() 不读 Data，此键仅写入关卡 JSON 备用；" +
                "要真正让关卡发放/使用某把铲子，请用下方「奖励 Reward」把收藏品设为该铲子（游戏唯一生效路径）。"},
    ],
    "Glove": [],
    "PacketPick": [
        {"k": "PendingRequestTimeoutSeconds", "label": "选卡请求超时(秒)", "t": "num", "def": 15},
        {"k": "PendingRequestSweepIntervalSeconds", "label": "超时扫描间隔(秒)", "t": "num", "def": 0.5},
        {"k": "PacketSelectionDebounceFrames", "label": "选卡防抖帧数", "t": "num", "def": 5},
        {"k": "ToolActivationGraceFrames", "label": "工具激活宽限帧", "t": "num", "def": 5},
        {"k": "CharacterTargetRadiusScale", "label": "目标半径缩放", "t": "num", "def": 0.6},
    ],
    "Mower": [
        {"k": "MowerPacketName", "label": "小推车卡牌", "t": "combo", "imp": "mowerItems"},
        {"k": "WaterMowerPacketName", "label": "水池小推车卡牌", "t": "combo", "imp": "mowerItems", "def": "MowerPoolCleaner"},
        {"k": "TargetZombiePacketName", "label": "目标僵尸卡牌", "t": "combo", "imp": "zombie", "def": "ZombieTarget"},
        {"k": "PreviewSpriteName", "label": "预览贴图", "t": "combo", "imp": "mowerItems", "def": "MowerDefault"},
        {"k": "MowerSpawnOffsetX", "label": "小推车X偏移", "t": "num", "def": 10},
        {"k": "TargetSpawnOffsetX", "label": "目标X偏移", "t": "num", "def": 40},
        {"k": "PreviewGroundOffset", "label": "预览贴地偏移", "t": "num", "def": 10},
        {"k": "PreviewTweenDuration", "label": "预览动画时长", "t": "num", "def": 0.5},
        {"k": "PreviewScale", "label": "预览缩放", "t": "num", "def": 1},
    ],
    "Brain": [
        {"k": "PacketName", "label": "脑子卡牌", "t": "combo", "imp": "item", "def": "ItemBrain"},
        {"k": "HorizontalOffset", "label": "水平偏移(±200)", "t": "num", "def": 10},
        {"k": "CharacterFilter", "label": "角色过滤", "t": "bool", "def": True},
    ],
    "NpcTalk": [
        {"k": "TalkName", "label": "对话名", "t": "text"},
        {"k": "StartDelay", "label": "开始延迟(秒)", "t": "num", "def": 1.5},
        {"k": "TemporaryBGM", "label": "临时BGM", "t": "combo", "imp": "bgm", "def": "MainMenu"},
        {"k": "isCustom", "label": "自定义对话(配 raw)", "t": "bool", "def": False},
    ],
    "Sun": [
        {"k": "Open", "label": "开启", "t": "bool", "def": True},
        {"k": "Type", "label": "阳光种类", "t": "sel", "imp": "sunType", "def": "Normal"},
        {"k": "Begin", "label": "初始阳光", "t": "num", "def": 300},
        {"k": "SpawnInterval", "label": "掉落间隔(秒)", "t": "num", "def": 12},
        {"k": "SpawnNum", "label": "掉落总数", "t": "num", "def": 50},
        {"k": "MovingMethod", "label": "移动方式", "t": "sel",
         "opts": [{"label": "落地 LAND", "value": "LAND"},
                  {"label": "重力 GRAVITY", "value": "GRAVITY"},
                  {"label": "移动 MOVING", "value": "MOVING"}], "def": "LAND"},
    ],
    "Progress": [
        {"k": "Mode", "label": "进度模式", "t": "sel",
         "opts": [{"label": "自动 Auto", "value": "Auto"},
                  {"label": "手动 Manual", "value": "Manual"}], "def": "Auto"},
        {"k": "LevelName", "label": "关卡名文本", "t": "text"},
        {"k": "DifficultyText", "label": "难度文本", "t": "text", "def": "DifficultText"},
        {"k": "SurvivalText", "label": "生存文本", "t": "text"},
        {"k": "ProgressText", "label": "进度文本", "t": "text", "def": "{value}/{max}"},
        {"k": "ProgressValue", "label": "进度值", "t": "num", "def": 0},
        {"k": "ProgressMax", "label": "进度上限", "t": "num", "def": 1},
        {"k": "AutoProgressResponse", "label": "自动进度响应(-1自动)", "t": "num", "def": -1},
        {"k": "DifficultyVisibility", "label": "难度可见性", "t": "sel", "opts": VIS_OPTS},
        {"k": "LevelNameVisibility", "label": "关卡名可见性", "t": "sel", "opts": VIS_OPTS},
        {"k": "SurvivalVisibility", "label": "生存可见性", "t": "sel", "opts": VIS_OPTS},
        {"k": "ProgressVisibility", "label": "进度可见性", "t": "sel", "opts": VIS_OPTS},
        {"k": "ProgressTextVisibility", "label": "进度文本可见性", "t": "sel", "opts": VIS_OPTS},
    ],
    "RainMode": [
        {"k": "Type", "label": "类型", "t": "sel",
         "opts": [{"label": "默认 Default", "value": "Default"},
                  {"label": "阳光雨 Sun", "value": "Sun"}], "def": "Default"},
        {"k": "AliveTime", "label": "存活时间(秒)", "t": "num", "def": 30},
        {"k": "Interval", "label": "掉落间隔(秒)", "t": "num", "def": 3},
        {"k": "Packet", "label": "掉落包", "t": "pkts"},
    ],
    "ConveyorBelt": [
        {"k": "Type", "label": "类型", "t": "text", "def": "Default"},
        {"k": "Interval", "label": "发包间隔(秒,≥0.05)", "t": "num", "def": 3},
        {"k": "IntervalIncreaseEvery", "label": "每N波提速", "t": "num", "def": 2},
        {"k": "IntervalMagnification", "label": "提速倍率", "t": "num", "def": 0.5},
        {"k": "MaxPacketCount", "label": "卡槽上限", "t": "num", "def": 14},
        {"k": "Packet", "label": "掉落包", "t": "pkts"},
        {"k": "PacketPrioritySpawnList", "label": "优先发包列表", "t": "prio"},
        {"k": "WaveEvent", "label": "波次事件", "t": "rawkey"},
    ],
    "PacketBank": [
        {"k": "PacketBankName", "label": "卡池名", "t": "sel", "imp": "packetBankAll", "req": True},
        {"k": "CategoryBatchSize", "label": "分类批量", "t": "num", "def": 256},
        {"k": "MaxPoolSize", "label": "池上限", "t": "num", "def": 96},
    ],
    "SeedBank": [
        {"k": "ColdDownStart", "label": "开局冷却", "t": "bool", "def": True},
        {"k": "ColdDownUse", "label": "使用冷却", "t": "bool", "def": True},
        {"k": "PlantColumn", "label": "种植列模式", "t": "bool", "def": False},
        {"k": "Method", "label": "供卡方式", "t": "sel",
         "opts": [{"label": "无 NOONE", "value": "NOONE"},
                  {"label": "选卡 CHOOSE", "value": "CHOOSE"},
                  {"label": "预设 PRESET", "value": "PRESET"},
                  {"label": "传送带 CONVEYOR", "value": "CONVEYOR"},
                  {"label": "加雨 RAIN", "value": "RAIN"}], "def": "NOONE"},
        {"k": "Packet", "label": "预选卡牌", "t": "plants"},
    ],
    "PreSpawn": [
        {"k": "MaxRetryPasses", "label": "重试上限", "t": "num", "def": 8},
        {"k": "Packet", "label": "预种植列表", "t": "prespawn"},
    ],
    "BGM": [
        {"k": "BackgroundMusic", "label": "背景音乐", "t": "sel", "imp": "bgm", "req": True},
        {"k": "BGMName", "label": "背景音乐(兼容键)", "t": "combo", "imp": "bgm"},
    ],
    "Fog": [
        {"k": "Open", "label": "开启迷雾", "t": "bool", "def": False},
        {"k": "BeginColumn", "label": "起始列", "t": "num", "def": 5},
        {"k": "ExtraColumns", "label": "额外列数", "t": "num", "def": 10},
        {"k": "BlowReturnDelay", "label": "吹雾回归延迟(秒)", "t": "num", "def": 25},
        {"k": "BlowDistance", "label": "吹雾距离", "t": "num", "def": 1400},
        {"k": "BlowDuration", "label": "吹雾时长(秒)", "t": "num", "def": 1.5},
        {"k": "ReturnDuration", "label": "回归时长(秒)", "t": "num", "def": 3},
        {"k": "EntryDuration", "label": "入场时长(秒)", "t": "num", "def": 3},
        {"k": "EntryStartX", "label": "入场起始X", "t": "num", "def": 1350},
    ],
    "LookStar": [],
    "ScreenEffect": [
        {"k": "StormOpen", "label": "暴雨效果", "t": "bool", "def": False},
        {"k": "PacketBankMethod", "label": "供卡方式", "t": "enumint",
         "opts": [["无 NOONE", 0], ["选卡 CHOOSE", 1], ["预设 PRESET", 2],
                  ["传送带 CONVEYOR", 3], ["加雨 RAIN", 4]], "def": 2},
    ],
    "WarningLine": [],
    "Portal": [],
    "Tutorial": [
        {"k": "TutorialName", "label": "教程名", "t": "text"},
        {"k": "isCustom", "label": "自定义教程(配 raw)", "t": "bool", "def": False},
    ],
    "Event": [
        {"k": "RemotePhaseTimeoutSeconds", "label": "联机阶段超时(秒)", "t": "num", "def": 10},
        {"k": "EventInit", "label": "初始化事件", "t": "rawkey"},
        {"k": "EventEntry", "label": "入场事件", "t": "rawkey"},
        {"k": "EventReady", "label": "就绪事件", "t": "rawkey"},
        {"k": "EventStart", "label": "开始事件", "t": "rawkey"},
    ],
    "Hammer": [],
    "SlotMachine": [
        {"k": "Open", "label": "开启", "t": "bool", "def": True},
        {"k": "AutoStart", "label": "自动开始", "t": "bool", "def": True},
        {"k": "Cost", "label": "单次消耗阳光", "t": "num", "def": 25},
        {"k": "Cooldown", "label": "冷却(秒)", "t": "num", "def": 0.5},
        {"k": "SpinDuration", "label": "转动时长(≥0.35)", "t": "num", "def": 1.25},
        {"k": "PacketAliveTime", "label": "卡牌存活时间(≥0.1)", "t": "num", "def": 15},
        {"k": "ClearSunReward", "label": "通关阳光奖励", "t": "num", "def": 0},
        {"k": "PacketList", "label": "转盘卡池", "t": "slots"},
        {"k": "ClosedText", "label": "关闭文本", "t": "text", "def": "CLOSED"},
        {"k": "SpinText", "label": "转动按钮文本", "t": "text", "def": "SPIN"},
    ],
}

# Wave 的简单顶层字段（波次列表由 waveEditor 专门编辑）
WAVE_SIMPLE_FIELDS = [
    {"k": "FlagZombieUse", "label": "使用旗帜僵尸", "t": "bool", "def": True},
    {"k": "FlagZombie", "label": "旗帜僵尸", "t": "text", "def": "ZombieFlag"},
    {"k": "FlagWaveInterval", "label": "旗帜波间隔", "t": "num", "def": 10},
    {"k": "MaxNextWaveHealthPercentage", "label": "下波血量上限比", "t": "num", "def": 0.15},
    {"k": "MinNextWaveHealthPercentage", "label": "下波血量下限比", "t": "num", "def": 0.2},
    {"k": "BeginCol", "label": "起始列", "t": "num", "def": 20},
    {"k": "SpawnColStart", "label": "出怪起始列", "t": "num", "def": 5},
    {"k": "SpawnColEnd", "label": "出怪结束列", "t": "num", "def": 20},
    {"k": "SpawnFrameBudgetMilliseconds", "label": "出怪帧预算(毫秒)", "t": "num", "def": 6},
    {"k": "SpawnMaxCharactersPerFrame", "label": "每帧最多出怪数", "t": "num", "def": 8},
    {"k": "ZombieInvisible", "label": "僵尸隐身", "t": "bool", "def": False},
]

# Wave 特有 raw 键（Survival 生存 endless 配置等）
WAVE_RAW_KEYS = [
    {"k": "Survival", "label": "Survival（生存配置）"},
    {"k": "CustomSurvival", "label": "CustomSurvival（自定义生存配置）"},
    {"k": "Dynamic", "label": "Dynamic（动态难度数组）"},
]

# Process 字段规格（Process.Name 决定 FinishMethod / 游戏模式）
PROCESS_SCHEMAS = {
    "Wave": [
        {"k": "MowerUse", "label": "使用小推车", "t": "bool", "def": False},
        {"k": "EntryBroadcastDuration", "label": "入场广播时长(≤15)", "t": "num", "def": 4},
        {"k": "CameraTravelDuration", "label": "镜头移动时长(≤10)", "t": "num", "def": 1.5},
        {"k": "PacketBankExitDelay", "label": "卡池退出延迟(≤5)", "t": "num", "def": 0.5},
        {"k": "EntryLabelDuration", "label": "入场标签时长(≤10)", "t": "num", "def": 2},
        {"k": "DebugEnterHouseFadeDuration", "label": "进屋淡出时长(≤5)", "t": "num", "def": 1},
    ],
    "Vase": [
        {"k": "Shuffle", "label": "打乱花瓶", "t": "bool", "def": False},
        {"k": "MowerUse", "label": "使用小推车", "t": "bool", "def": False},
        {"k": "PacketBankMethod", "label": "供卡方式(0-4或枚举名)", "t": "text", "def": 0},
        {"k": "PacketBankExitDelay", "label": "卡池退出延迟(≤5)", "t": "num", "def": 0.5},
        {"k": "Vase", "label": "花瓶列表", "t": "vases"},
        {"k": "VaseFill", "label": "填瓶列表", "t": "vasefill"},
    ],
    "IZM": [
        {"k": "Shuffle", "label": "打乱", "t": "bool", "def": True},
        {"k": "PreSpawnMaxRetryPasses", "label": "预种植重试上限(1-64)", "t": "num", "def": 8},
        {"k": "FailureCheckIntervalFrames", "label": "失败检查帧间隔(1-120)", "t": "num", "def": 6},
        {"k": "PacketBankExitDelay", "label": "卡池退出延迟(≤5)", "t": "num", "def": 0.5},
        {"k": "EnterHouseFadeDuration", "label": "进屋淡出时长(≤5)", "t": "num", "def": 1},
        {"k": "FailureIgnoredZombieName", "label": "失败判定忽略僵尸", "t": "text", "def": "ZombieTarget"},
    ],
    "IZM2": [
        {"k": "MowerUse", "label": "使用小推车", "t": "bool", "def": False},
        {"k": "EntryBroadcastDuration", "label": "入场广播时长(≤15)", "t": "num", "def": 4},
        {"k": "CameraTravelDuration", "label": "镜头移动时长(≤10)", "t": "num", "def": 1.5},
        {"k": "PacketBankExitDelay", "label": "卡池退出延迟(≤5)", "t": "num", "def": 0.5},
        {"k": "EntryLabelDuration", "label": "入场标签时长(≤10)", "t": "num", "def": 2},
        {"k": "DebugEnterHouseFadeDuration", "label": "进屋淡出时长(≤5)", "t": "num", "def": 1},
    ],
    "Quiz": [
        {"k": "AutoStripColumn", "label": "自动计算剥离列", "t": "bool", "def": True},
        {"k": "StripColumn", "label": "剥离列(1-64)", "t": "num", "def": 5},
        {"k": "PotPacketName", "label": "花盆卡牌", "t": "text", "def": "PlantPot"},
        {"k": "LilyPadPacketName", "label": "荷叶卡牌", "t": "text", "def": "PlantLilyPad"},
        {"k": "PresentBoxPacketName", "label": "礼盒植物卡牌", "t": "text", "def": "PlantPresentBox"},
        {"k": "ZombieVasePacketName", "label": "僵尸罐卡牌", "t": "text", "def": "VaseZombie"},
        {"k": "PresentBoxPacketBank", "label": "礼盒卡池", "t": "text", "def": "PresentBoxNoAshPlant"},
        {"k": "ZombieVasePacketBank", "label": "僵尸罐卡池", "t": "text", "def": "QuizZombie"},
        {"k": "SettlementLineDelay", "label": "结算行延迟(≤10)", "t": "num", "def": 1},
        {"k": "SettlementSummaryDelay", "label": "结算汇总延迟(≤10)", "t": "num", "def": 2},
        {"k": "CoinSpawnInterval", "label": "金币生成间隔(≤2)", "t": "num", "def": 0.1},
        {"k": "CoinFlightDelay", "label": "金币飞行延迟(≤10)", "t": "num", "def": 1},
        {"k": "CoinCollectDelay", "label": "金币收取延迟(≤10)", "t": "num", "def": 0.5},
    ],
    "Empty": [],
}

PROCESS_TIPS = {
    "Wave": "常规波次模式（FinishMethod=Wave）",
    "Vase": "花瓶模式（FinishMethod=Vase）",
    "IZM": "我是僵尸模式（FinishMethod=IZM）",
    "IZM2": "我是僵尸2模式（FinishMethod=IZM2）",
    "Quiz": "答题模式（FinishMethod=Quiz）",
    "Empty": "空过程（FinishMethod=EMPTY，由 Feature 自行控制结束）",
}

# ---- NpcTalk 的 Arg 预设（游戏侧 NpcTalkHandConfig/NpcTalkTutorialConfig 的 Arg 是资源路径） ----
# Hand 模式: [手, 肩, 肩2, 头]  ← 植物/僵尸场景；Tutorial 模式: [教程配置]
# 复用官方 talkArg 的 import 规则: import:plant[uid:value],zombie[uid:value],... ,talkArgOther
def _build_talk_arg_presets():
    out = []
    seen = set()
    for key in ("plant", "zombie", "zombieExtra", "item"):
        for it in opt.get(key, []):
            if not isinstance(it, dict):
                continue
            uid = it.get("uid")
            lab = it.get("label")
            if not uid or not lab or uid in seen:
                continue
            seen.add(uid)
            out.append({"label": lab, "value": uid})
    for it in opt.get("talkArgOther", []):
        if not isinstance(it, dict):
            continue
        lab = it.get("label")
        uid = it.get("uid") or it.get("value")
        if not lab or not uid or uid in seen:
            continue
        seen.add(uid)
        out.append({"label": lab, "value": uid})
    return out


talk_arg_presets = _build_talk_arg_presets()

# ---- 铲子预设（游戏侧 ShovelResource.json 共 11 把；中文取自 Translate.csv 的 *_SHOVEL_*_NAME） ----
SHOVEL_LABELS = {
    "ShovelDefault": "铁铲",
    "ShovelGold": "金铲",
    "ShovelCold": "寒冰铲",
    "ShovelDiamond": "钻石铲",
    "ShovelJalapeno": "辣椒铲",
    "ShovelMagnet": "磁力铲",
    "ShovelWatermelon": "西瓜铲",
    "ShovelPumpkin": "南瓜铲",
    "ShovelCaptain": "海盗铲",
    "ShovelSkeleton": "骷髅铲",
    "ShovelExplode": "爆能铲",
}
shovel_presets = [{"label": v, "value": k} for k, v in SHOVEL_LABELS.items()]

DATA = {
    "plant": slim(opt.get("plant", [])),
    "zombie": slim(opt.get("zombie", [])),
    "zombieExtra": slim(opt.get("zombieExtra", [])),
    "item": slim(opt.get("item", [])),
    "ball": ball_list,
    "armor": armor_out,
    "armorWls": _armor_wls,
    "projectile": slim(opt.get("projectile", [])),
    "map": slim(opt.get("map", [])),
    "bgm": slim(opt.get("bgm", [])),
    "produceType": slim(opt.get("produceType", [])),
    "cardType": slim(opt.get("cardType", [])),
    "collectable": slim(opt.get("collectable", [])),
    "packetBankAll": slim(opt.get("packetBankAll", [])),
    "modulatePresets": slim(opt.get("modulatePresets", [])),
    "sunType": slim(opt.get("sunType", [])),
    "packetBankType": slim(opt.get("packetBankType", [])),
    "categoryName": slim(opt.get("categoryName", [])),
    "talkNpc": slim(opt.get("talkNpc", [])),
    "talkAudio": slim(opt.get("talkAudio", [])),
    "talkAnime": slim(opt.get("talkAnime", [])),
    "talkArg": slim(opt.get("talkArg", [])),
    "talkArgOther": slim(opt.get("talkArgOther", [])),
    "talkArgPresets": talk_arg_presets,
    "shovels": shovel_presets,
    "talkModes": TALK_MODES,
    "mowerItems": mower_items,
    "cardAttributes": card_attrs,
    "screenEffectMethods": SCREEN_EFFECT_METHODS,
    "tutorialConditions": TUTORIAL_CONDITIONS,
    "property": prop_out,
    "attribute": tpl.get("attribute", []),
    "event": event_out,
    "classTypeComputed": tpl.get("classTypeComputed", {}),
    "gmFields": gm_fields,
    "featureOrder": FEATURE_ORDER,
    "featureNames": FEATURE_NAMES,
    "featureLabels": FEATURE_LABELS,
    "processNames": PROCESS_NAMES,
    "processLabels": PROCESS_LABELS,
    "featureSchemas": FEATURE_SCHEMAS,
    "waveSimpleFields": WAVE_SIMPLE_FIELDS,
    "waveRawKeys": WAVE_RAW_KEYS,
    "processSchemas": PROCESS_SCHEMAS,
    "processTips": PROCESS_TIPS,
    "template": level_tmpl,
    "meta": {
        "generatedBy": "build_gemmatch_builder.py",
        "plant": len(opt.get("plant", [])),
        "zombie": len(opt.get("zombie", [])),
        "zombieExtra": len(opt.get("zombieExtra", [])),
        "item": len(opt.get("item", [])),
        "armor": len(opt.get("armor", [])),
        "property": len(prop_out),
        "attribute": len(tpl.get("attribute", [])),
        "event": len(event_out),
    },
}

HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>关卡构建器 · 全模式</title>
<style>
:root{
  --bg:#14161a; --panel:#1c1f26; --panel2:#23272f; --line:#31363f;
  --fg:#e6e8ec; --dim:#9aa3b2; --accent:#4c9ffe; --ok:#3fb950; --warn:#d29922; --err:#f85149;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font:14px/1.6 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
header{position:sticky;top:0;z-index:50;background:var(--panel);border-bottom:1px solid var(--line);
  padding:10px 16px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
header h1{font-size:16px;margin:0 12px 0 0;font-weight:600}
header .sp{flex:1}
button{background:var(--panel2);color:var(--fg);border:1px solid var(--line);
  border-radius:6px;padding:6px 12px;cursor:pointer;font-size:13px}
button:hover{background:#2c313a;border-color:var(--accent)}
button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
button.danger{color:var(--err)}
main{max-width:1100px;margin:0 auto;padding:18px 16px 60px}
section{background:var(--panel);border:1px solid var(--line);border-radius:8px;
  margin-bottom:14px;overflow:hidden}
section>h2{margin:0;padding:10px 14px;background:var(--panel2);font-size:14px;
  border-bottom:1px solid var(--line);display:flex;align-items:center;gap:8px}
section>h2 .tag{font-size:11px;color:var(--dim);font-weight:400}
.body{padding:12px 14px}
.row{display:flex;align-items:center;gap:10px;margin:7px 0}
.row>label{width:190px;flex:none;color:var(--dim);font-size:13px}
.row>.ctl{flex:1;min-width:0}
/* 全宽纵向块：标题独占一行、内容在下方整行展开。
   用于「嵌套覆盖」——避免塞进 .row>.ctl 右侧变窄而无法编辑。 */
.stack{width:100%;display:block;margin:10px 0;padding:8px 0 8px 10px;
  border-left:3px solid var(--accent);background:#15181e;border-radius:0 6px 6px 0}
.stack>.stackhd{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.stack>.stackhd .ttl{font-weight:600;font-size:13px;color:var(--fg)}
.stack>.stackhd .sp{flex:1}
.stack>.stackbody{width:100%;min-width:0}
.stack .row>label{width:150px}
/* 嵌套层再收窄标签，保证深层输入框也够宽 */
.stack .stack .row>label{width:120px}
input[type=text],input[type=number],select,textarea{
  background:#11141a;color:var(--fg);border:1px solid var(--line);border-radius:5px;
  padding:5px 8px;font:13px inherit;width:100%}
textarea{font-family:ui-monospace,Consolas,monospace;font-size:12px;min-height:60px;resize:vertical}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--accent)}
.hint{color:var(--dim);font-size:12px;margin:2px 0 0}
.card{border:1px solid var(--line);border-radius:6px;padding:10px;margin:8px 0;background:#181b21}
.card>.hd{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.card>.hd .ttl{font-weight:600;font-size:13px}
.card>.hd .sp{flex:1}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:6px}
.chip{background:#2a3140;border:1px solid var(--line);border-radius:12px;
  padding:2px 8px;font-size:12px;display:inline-flex;gap:6px;align-items:center}
.chip b{cursor:pointer;color:var(--err);font-weight:700}
.plist{border:1px solid var(--line);border-radius:5px;max-height:210px;overflow:auto;
  background:#11141a;padding:6px}
.pitem{padding:3px 6px;cursor:pointer;border-radius:4px;font-size:13px}
.pitem:hover{background:#2a3140}
.pempty{color:var(--dim);font-size:12px;padding:4px 6px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{border:1px solid var(--line);padding:4px 7px;text-align:left}
th{background:var(--panel2);color:var(--dim);font-weight:500}
.ro{color:var(--dim);font-style:italic}
#report{white-space:pre-wrap;font-family:ui-monospace,Consolas,monospace;font-size:12px}
.ok{color:var(--ok)}.bad{color:var(--err)}.wn{color:var(--warn)}
details>summary{cursor:pointer;color:var(--dim);font-size:13px;margin:6px 0}
</style>
</head>
<body>
<header>
  <h1>关卡构建器 · 全模式</h1>
  <span id="stat" class="tag" style="color:var(--dim);font-size:12px"></span>
  <span class="sp"></span>
  <button id="btnNew">新建</button>
  <button onclick="document.getElementById('fileInput').click()">导入 JSON</button>
  <input id="fileInput" type="file" accept=".json" style="display:none">
  <button id="btnValidate">校验</button>
  <button class="primary" id="btnExport" title="优先弹出系统保存对话框，可自选文件夹与文件名">导出 JSON</button>
</header>
<main id="app"></main>

<script id="DATA" type="application/json">__DATA__</script>
<script>
(function(){
"use strict";
window.addEventListener('error', function(ev){
  var st = document.getElementById('stat');
  if(st) st.textContent = '脚本错误: ' + (ev.message || ev.type) + ' @' + (ev.lineno||'?') + ':' + (ev.colno||'?');
});
var DATA = JSON.parse(document.getElementById('DATA').textContent);
var FORDER = DATA.featureOrder;
var PROPS_ALL = (function(){ // ka(): 同 value 只保留最靠前一条（与原构建器一致，含既有 quirk）
  var seen = {}, out = [];
  DATA.property.forEach(function(p){ if(!seen[p.value]){ seen[p.value]=1; out.push(p); } });
  return out;
})();

/* ---------- 工具 ---------- */
function el(tag, attrs, kids){
  var e = document.createElement(tag);
  if(attrs) for(var k in attrs){
    if(k === 'class') e.className = attrs[k];
    else if(k === 'text') e.textContent = attrs[k];
    else if(k.slice(0,2) === 'on') e.addEventListener(k.slice(2), attrs[k]);
    else if(attrs[k] !== null && attrs[k] !== undefined) e.setAttribute(k, attrs[k]);
  }
  (kids||[]).forEach(function(c){ if(c) e.appendChild(c); });
  return e;
}
function row(label, control, tip){
  var l = el('label',{text:label});
  var wrap = el('div',{class:'ctl'},[control]);
  if(tip) wrap.appendChild(el('div',{class:'hint',text:tip}));
  return el('div',{class:'row'},[l,wrap]);
}
function section(title, tag, bodyKids){
  var h = el('h2',{},[el('span',{text:title})]);
  if(tag) h.appendChild(el('span',{class:'tag',text:tag}));
  var b = el('div',{class:'body'},bodyKids);
  return el('section',{},[h,b]);
}
function val(v,d){ return (v===undefined||v===null||v==='')?d:v; }

/* opts 归一化：字符串数组 → [{label,value}]（label=value）；对象数组原样返回。
   让 schema 里可以直接写 "opts":[{"label":"显示","value":"Show"}] 或 ["Show"]。 */
function normOpts(o){
  if(!Array.isArray(o) || !o.length) return [];
  return (o[0] && typeof o[0] === 'object')
    ? o.map(function(x){ return {label:val(x.label,x.value), value:x.value}; })
    : o.map(function(x){ return {label:x, value:x}; });
}

/* 全宽纵向块：标题在上、内容在下方整行展开。
   用于「嵌套覆盖」——避免塞进 .row>.ctl 右侧被挤窄而无法编辑（对齐官方构建器观感）。 */
function stackBlock(titleText, content, headExtra){
  var hd = el('div',{class:'stackhd'},[el('span',{class:'ttl',text:titleText})]);
  if(headExtra) hd.appendChild(headExtra);
  return el('div',{class:'stack'},[hd, el('div',{class:'stackbody'},[content])]);
}

/* ---------- import: 解析（对应原构建器 uh()） ---------- */
function resolveImport(spec){
  if(!spec || spec.indexOf('import:')!==0) return null;
  var out = [];
  spec.slice(7).split(',').forEach(function(p){
    var m = p.match(/^([^\[]+)(?:\[([^\]]+)\])?$/);
    if(!m) return;
    var key = m[1], filter = m[2];
    var arr = DATA[key];
    if(!arr && key === 'other') arr = DATA.item;
    if(!arr) return;
    if(filter && key === 'item' && filter === 'ball') arr = DATA.ball;
    out = out.concat(arr);
  });
  return out;
}

/* ---------- 控件 ---------- */
function txtInput(get, set, ph){
  var i = el('input',{type:'text', value:val(get(),''), placeholder:ph||''});
  i.addEventListener('input', function(){ set(i.value); });
  return i;
}
/* 多行文本（支持换行，Enter 直接换行；JSON 里保存为含 \n 的字符串） */
function taInput(get, set, ph, minH){
  var t = el('textarea',{placeholder:ph||'', style:'min-height:'+(minH||54)+'px'});
  t.value = val(get(),'');
  t.addEventListener('input', function(){ set(t.value); });
  return t;
}
function numInput(get, set, step){
  var i = el('input',{type:'number', value:(get()===undefined||get()===null?'':get()), step:step||'1'});
  i.addEventListener('input', function(){ set(i.value===''?null:Number(i.value)); });
  return i;
}
function boolInput(get, set){
  var i = el('input',{type:'checkbox', style:'width:auto'});
  i.checked = !!get();
  i.addEventListener('change', function(){ set(i.checked); });
  return el('div',{},[i]);
}
function selInput(get, set, options, allowEmpty){
  var s = el('select',{});
  if(allowEmpty !== false) s.appendChild(el('option',{value:'',text:'(未设置)'}));
  options.forEach(function(o){ s.appendChild(el('option',{value:o.value,text:o.label})); });
  s.value = val(get(),'');
  s.addEventListener('change', function(){ set(s.value); });
  return s;
}
/* 多选：已选 chips + 搜索列表（应对 324 植物的规模） */
function multiPicker(get, set, options){
  var box = el('div',{});
  function render(){
    box.innerHTML = '';
    var sel = get() || [];
    var chips = el('div',{class:'chips'});
    if(!sel.length) chips.appendChild(el('span',{class:'hint',text:'（未选择）'}));
    sel.forEach(function(v,i){
      var o = options.filter(function(x){return x.value===v;})[0];
      chips.appendChild(el('span',{class:'chip'},[
        el('span',{text:o?o.label:v}),
        el('b',{text:'×', title:'移除', onclick:function(){ sel.splice(i,1); set(sel); render(); }})
      ]));
    });
    box.appendChild(chips);
    var search = el('input',{type:'text',placeholder:'搜索并点击添加…'});
    var list = el('div',{class:'plist'});
    function fill(){
      list.innerHTML = '';
      var q = search.value.trim().toLowerCase();
      var shown = 0;
      options.forEach(function(o){
        if(sel.indexOf(o.value)>=0) return;
        if(q && (o.label+o.value).toLowerCase().indexOf(q)<0) return;
        shown++;
        if(shown>300) return;
        list.appendChild(el('div',{class:'pitem',text:o.label+'  ('+o.value+')',
          onclick:function(){ sel.push(o.value); set(sel); render(); }}));
      });
      if(!shown) list.appendChild(el('div',{class:'pempty',text:'无匹配项'}));
    }
    search.addEventListener('input', fill);
    fill();
    box.appendChild(search);
    box.appendChild(list);
  }
  render();
  return box;
}

/* 原始 JSON 值编辑：解析失败标红但保留原文，不丢数据 */
function rawJsonCtl(get, set){
  var t = el('textarea',{style:'min-height:38px'});
  var cur = get();
  t.value = (cur===undefined||cur===null)?'':JSON.stringify(cur);
  t.addEventListener('input', function(){
    var s = t.value.trim();
    if(!s){ set(null); t.style.borderColor=''; return; }
    try{ set(JSON.parse(s)); t.style.borderColor=''; }
    catch(e){ t.style.borderColor='#f85149'; }
  });
  return t;
}

/* 带中文标签的预设控件：下拉显示 label（中文），选中写 value；仍可自由输入 */
function labelCombo(get, set, options, ph){
  var wrap = el('span',{style:'display:flex;gap:6px;flex:1'});
  var sel = el('select',{style:'max-width:46%'});
  function fillSel(){
    sel.innerHTML='';
    var cur = val(get(),'');
    var matched = false;
    sel.appendChild(el('option',{value:'', text:'（从预设选择…）'}));
    (options||[]).forEach(function(o){
      var op = el('option',{value:o.value, text:o.label+'  ·  '+o.value});
      if(o.value===cur){ op.selected = true; matched = true; }
      sel.appendChild(op);
    });
    if(cur && !matched){
      var op2 = el('option',{value:cur, text:'（自定义）'+cur});
      op2.selected = true; sel.appendChild(op2);
    }
  }
  fillSel();
  var inp = el('input',{type:'text', value:val(get(),''), placeholder:ph||'自由输入…', style:'flex:1'});
  sel.addEventListener('change', function(){
    if(sel.value==='') return;
    inp.value = sel.value;
    set(sel.value);
  });
  inp.addEventListener('input', function(){ set(inp.value); fillSel(); });
  wrap.appendChild(sel);
  wrap.appendChild(inp);
  return wrap;
}

/* ---------- 勾选批量加入（属性覆盖用） ---------- */
function propChecklist(options, isChosen, onAdd){
  var box = el('div',{});
  var search = el('input',{type:'text',placeholder:'搜索属性…'});
  var list = el('div',{class:'plist'});
  function fill(){
    list.innerHTML='';
    var q = search.value.trim().toLowerCase(); var shown=0;
    options.forEach(function(p){
      if(isChosen(p.value)) return;
      if(q && (p.label+p.value).toLowerCase().indexOf(q)<0) return;
      shown++;
      var cb = el('input',{type:'checkbox',style:'width:auto'});
      cb.setAttribute('data-v', p.value);
      list.appendChild(el('label',{class:'pitem',style:'display:flex;gap:6px;align-items:center;cursor:pointer'},
        [cb, el('span',{text:p.label+' ('+p.value+')'})]));
    });
    if(!shown) list.appendChild(el('div',{class:'pempty',text:'无匹配项或已全部加入'}));
  }
  search.addEventListener('input', fill);
  fill();
  var btn = el('button',{text:'＋ 批量加入勾选',onclick:function(){
    var picked=[];
    var cbs = list.querySelectorAll('input[type=checkbox]');
    for(var k=0;k<cbs.length;k++){ if(cbs[k].checked) picked.push(cbs[k].getAttribute('data-v')); }
    if(!picked.length){ alert('请先勾选要加入的属性'); return; }
    onAdd(picked);
  }});
  box.appendChild(search); box.appendChild(list); box.appendChild(btn);
  return box;
}

/* ---------- 卡牌覆盖编辑器（TowerDefensePacketOverride） ---------- */
var CARD_ATTRS = DATA.cardAttributes || [];
function cardOverrideFields(obj){
  var box = el('div',{});
  CARD_ATTRS.forEach(function(a){
    var prop = a.property || {}, ty = prop.type, key = a.value;
    if(ty === 'attributes'){
      /* 嵌套覆盖：全宽纵向展开在「上面卡牌覆盖」的下面，而不是挤进 .row>.ctl 右侧。
         官方构建器同样是「属性覆盖」另起一块，避免深层输入框太靠右无法编辑。 */
      var holder = el('div',{});
      function drawOvr(){
        holder.innerHTML='';
        if(obj[key] === undefined){
          holder.appendChild(el('button',{text:'＋ 配置 '+a.label,onclick:function(){ obj[key]={}; drawOvr(); }}));
        }else{
          holder.appendChild(el('button',{class:'danger',text:'✕ 清除 '+a.label,onclick:function(){ delete obj[key]; drawOvr(); }}));
          holder.appendChild(overrideEditor(obj[key], a.label, {mode:'plant'}));
        }
      }
      drawOvr();
      box.appendChild(stackBlock(a.label+' ('+key+')', holder));
    }else if(ty === 'event-table'){
      box.appendChild(row(a.label+' ('+key+')',
        eventListEditor(function(){return obj[key];}, function(v){ if(v&&v.length) obj[key]=v; else delete obj[key]; }, key)));
    }else if(ty === 'switch'){
      var c = el('input',{type:'checkbox',style:'width:auto'});
      c.checked = (key in obj) ? !!obj[key] : !!prop.default;
      c.addEventListener('change',function(){ obj[key]=c.checked; });
      box.appendChild(row(a.label+' ('+key+')', el('div',{},[c]),
        (prop.onText? ('开='+prop.onText+'；关='+(prop.offText||'')) : null)));
    }else if(ty === 'select'){
      box.appendChild(row(a.label+' ('+key+')',
        selInput(function(){return obj[key];}, function(v){ if(v==='') delete obj[key]; else obj[key]=v; },
          resolveImport(prop.options)||[], true)));
    }else if(ty === 'range-number'){
      var o0 = obj[key]||{};
      var x = el('input',{type:'number',step:'any',placeholder:'min',value:(o0[0]===undefined?'':o0[0])});
      var y = el('input',{type:'number',step:'any',placeholder:'max',value:(o0[1]===undefined?'':o0[1])});
      function upd(){ if(x.value===''&&y.value===''){ delete obj[key]; return; }
        obj[key]=[x.value===''?-1:Number(x.value), y.value===''?-1:Number(y.value)]; }
      x.addEventListener('input',upd); y.addEventListener('input',upd);
      box.appendChild(row(a.label+' ('+key+')', el('div',{},[x,y]), '区间[min,max]'));
    }else if(ty === 'number'){
      box.appendChild(row(a.label+' ('+key+')',
        numInput(function(){return obj[key];}, function(v){ if(v===null) delete obj[key]; else obj[key]=v; }, 'any')));
    }else{
      box.appendChild(row(a.label+' ('+key+')',
        txtInput(function(){return obj[key];}, function(v){ if(v==='') delete obj[key]; else obj[key]=v; })));
    }
  });
  return box;
}
function packetOverrideEditor(p, rerender){
  var box = el('div',{style:'flex-basis:100%;border-top:1px dashed #31363f;margin-top:5px;padding-top:5px'});
  function draw(){
    box.innerHTML='';
    if(p.Override === undefined){
      box.appendChild(el('button',{text:'＋ 编辑卡牌覆盖（品质/价格/涨价/格数/直接种植/属性覆盖）',
        onclick:function(){ p.Override={}; draw(); if(rerender) rerender(); }}));
    }else{
      box.appendChild(el('div',{style:'display:flex;align-items:center;gap:8px'},[
        el('b',{text:'卡牌覆盖 Override'}),
        el('span',{style:'flex:1'}),
        el('button',{class:'danger',text:'✕ 清除',onclick:function(){ delete p.Override; draw(); if(rerender) rerender(); }})
      ]));
      box.appendChild(cardOverrideFields(p.Override));
    }
  }
  draw();
  return box;
}

/* ---------- NpcTalk 参数 Arg 列表编辑器（预设 + 自由输入） ---------- */
function argListEditor(t){
  var box = el('div',{class:'card'});
  box.appendChild(el('div',{class:'hd'},[
    el('span',{class:'ttl',text:'参数 Arg[]'}),
    el('span',{class:'hint',text:'伸手 Hand=[手,肩,肩2,头]；教程 Tutorial=[教程配置]'})
  ]));
  function render(){
    while(box.childNodes.length>1) box.removeChild(box.lastChild);
    var list = t.Arg || [];          // 只读遍历，不主动建空数组（避免导出 "Arg":[] 噪声）
    list.forEach(function(v,i){
      var line = el('div',{style:'display:flex;gap:6px;align-items:flex-start;margin:4px 0'});
      var wrap = el('div',{style:'flex:1'});
      wrap.appendChild(labelCombo(
        function(){return v;},
        function(nv){ t.Arg[i]=nv; },
        DATA.talkArgPresets,
        '槽位 '+(i+1)+'：从预设选择，或直接填 uid:// 路径'
      ));
      line.appendChild(wrap);
      line.appendChild(el('button',{text:'↑',onclick:function(){ if(i>0){var x=t.Arg[i-1];t.Arg[i-1]=t.Arg[i];t.Arg[i]=x;render();} }}));
      line.appendChild(el('button',{text:'↓',onclick:function(){ if(i<t.Arg.length-1){var x=t.Arg[i+1];t.Arg[i+1]=t.Arg[i];t.Arg[i]=x;render();} }}));
      line.appendChild(el('button',{class:'danger',text:'✕',onclick:function(){
        t.Arg.splice(i,1); if(!t.Arg.length) delete t.Arg; render();
      }}));
      box.appendChild(line);
    });
    box.appendChild(el('button',{text:'＋ 添加槽位',onclick:function(){ t.Arg=t.Arg||[]; t.Arg.push(''); render(); }}));
    var ta = el('textarea',{style:'min-height:44px;margin-top:6px', placeholder:'每行一个 uid:// 路径（也可粘贴后点「从文本导入」）'});
    var btns = el('div',{style:'display:flex;gap:6px;align-items:center'});
    btns.appendChild(el('button',{text:'从文本导入',onclick:function(){
      var arr = ta.value.split('\n').map(function(s){return s.trim();}).filter(function(s){return s!=='';});
      if(arr.length) t.Arg = arr; else delete t.Arg; render();
    }}));
    btns.appendChild(el('span',{class:'hint',text:'批量粘贴用；导入后可用上方槽位微调'}));
    box.appendChild(ta);
    box.appendChild(btns);
  }
  render();
  return box;
}

/* ---------- NpcTalk 自定义对话编辑器 ---------- */
function talkEditor(data){
  var box = el('div',{class:'card'});
  box.appendChild(el('div',{class:'hd'},[el('span',{class:'ttl',text:'自定义对话 Talk[]'})]));
  function render(){
    while(box.childNodes.length>1) box.removeChild(box.lastChild);
    data.Talk = data.Talk || [];
    data.Talk.forEach(function(t,i){
      var card = el('div',{class:'card'});
      card.appendChild(el('div',{class:'hd'},[
        el('span',{class:'ttl',text:'对话 '+(i+1)}),
        el('span',{style:'flex:1'}),
        el('button',{text:'↑',onclick:function(){ if(i>0){var x=data.Talk[i-1];data.Talk[i-1]=t;data.Talk[i]=x;render();} }}),
        el('button',{text:'↓',onclick:function(){ if(i<data.Talk.length-1){var x=data.Talk[i+1];data.Talk[i+1]=t;data.Talk[i]=x;render();} }}),
        el('button',{class:'danger',text:'删除',onclick:function(){ data.Talk.splice(i,1); if(!data.Talk.length) delete data.Talk; render(); }})
      ]));
      card.appendChild(row('模式 Mode', selInput(function(){return t.Mode;}, function(v){ if(v==='') delete t.Mode; else t.Mode=v; }, DATA.talkModes, true)));
      card.appendChild(row('NPC', selInput(function(){return t.Npc;}, function(v){ if(v==='') delete t.Npc; else t.Npc=v; }, DATA.talkNpc, true)));
      card.appendChild(row('文本 Text',
        taInput(function(){return t.Text;}, function(v){ if(v==='') delete t.Text; else t.Text=v; },
          '可换行（Enter 换行）；填写本地化键（如 NPC_TALK_LEVEL1_1_TUTORIAL_1）或直接写文本', 54)));
      card.appendChild(row('动画 Anime', selInput(function(){return t.Anime;}, function(v){ if(v==='') delete t.Anime; else t.Anime=v; }, DATA.talkAnime, true)));
      card.appendChild(row('音频 Audio', selInput(function(){return t.Audio;}, function(v){ if(v==='') delete t.Audio; else t.Audio=v; }, DATA.talkAudio, true)));
      card.appendChild(argListEditor(t));
      box.appendChild(card);
    });
    box.appendChild(el('button',{text:'＋ 添加对话',onclick:function(){ data.Talk=data.Talk||[]; data.Talk.push({Mode:'Default'}); render(); }}));
  }
  render();
  return box;
}

/* ---------- Tutorial 自定义教程编辑器 ---------- */
function tutorialEditor(data){
  var box = el('div',{class:'card'});
  box.appendChild(el('div',{class:'hd'},[el('span',{class:'ttl',text:'自定义教程 Step[]'})]));
  function render(){
    while(box.childNodes.length>1) box.removeChild(box.lastChild);
    data.Step = data.Step || [];
    data.Step.forEach(function(st,i){
      var card = el('div',{class:'card'});
      card.appendChild(el('div',{class:'hd'},[
        el('span',{class:'ttl',text:'步骤 '+(i+1)}),
        el('span',{style:'flex:1'}),
        el('button',{text:'↑',onclick:function(){ if(i>0){var x=data.Step[i-1];data.Step[i-1]=st;data.Step[i]=x;render();} }}),
        el('button',{text:'↓',onclick:function(){ if(i<data.Step.length-1){var x=data.Step[i+1];data.Step[i+1]=st;data.Step[i]=x;render();} }}),
        el('button',{class:'danger',text:'删除',onclick:function(){ data.Step.splice(i,1); if(!data.Step.length) delete data.Step; render(); }})
      ]));
      st.BroadCast = st.BroadCast || {};
      card.appendChild(row('广播文本 BroadCast.Text',
        taInput(function(){return st.BroadCast.Text;}, function(v){ if(v==='') delete st.BroadCast.Text; else st.BroadCast.Text=v; },
          '可换行（Enter 换行）', 54)));
      card.appendChild(row('广播时长 BroadCast.Time', numInput(function(){return st.BroadCast.Time;}, function(v){ if(v===null) delete st.BroadCast.Time; else st.BroadCast.Time=v; }, 'any'), '-1=常驻'));
      var condBox = el('div',{});
      function drawConds(){
        condBox.innerHTML='';
        st.Condition = st.Condition || [];
        st.Condition.forEach(function(cd,ci){
          var c = el('div',{class:'card'});
          c.appendChild(el('div',{class:'hd'},[
            el('span',{class:'ttl',text:'条件 '+(ci+1)}),
            el('span',{style:'flex:1'}),
            el('button',{class:'danger',text:'删除',onclick:function(){ st.Condition.splice(ci,1); if(!st.Condition.length) delete st.Condition; drawConds(); }})
          ]));
          c.appendChild(row('条件名 Name',
            selInput(function(){return cd.Name;}, function(v){ cd.Name=v; if(!cd.Data) cd.Data={}; drawConds(); },
              (DATA.tutorialConditions||[]).map(function(x){return {label:x.label,value:x.name};}), false)));
          var spec = (DATA.tutorialConditions||[]).filter(function(x){return x.name===cd.Name;})[0];
          if(spec){
            cd.Data = cd.Data || {};
            (spec.fields||[]).forEach(function(f){
              if(f.t==='combo'){
                c.appendChild(row(f.label+' ('+f.k+')',
                  labelCombo(function(){return cd.Data[f.k];}, function(v){ if(v==='') delete cd.Data[f.k]; else cd.Data[f.k]=v; },
                    resolveImport('import:'+f.imp)||[])));
              }else if(f.t==='enum'){
                c.appendChild(row(f.label+' ('+f.k+')',
                  selInput(function(){return cd.Data[f.k];}, function(v){ if(v==='') delete cd.Data[f.k]; else cd.Data[f.k]=v; },
                    normOpts(f.opts), true)));
              }else{
                c.appendChild(row(f.label+' ('+f.k+')',
                  numInput(function(){return cd.Data[f.k];}, function(v){ if(v===null) delete cd.Data[f.k]; else cd.Data[f.k]=v; }, 'any')));
              }
            });
          }
          condBox.appendChild(c);
        });
        condBox.appendChild(el('button',{text:'＋ 添加条件',onclick:function(){ st.Condition=st.Condition||[]; st.Condition.push({Name:'CheckCharacterNum',Data:{}}); drawConds(); }}));
      }
      drawConds();
      card.appendChild(row('条件 Condition[]', condBox));
      box.appendChild(card);
    });
    box.appendChild(el('button',{text:'＋ 添加步骤',onclick:function(){ data.Step=data.Step||[]; data.Step.push({BroadCast:{Text:'',Time:-1},Condition:[]}); render(); }}));
  }
  render();
  return box;
}

/* ---------- 全模式：字段规格编辑器 ---------- */
var SCHEMAS = DATA.featureSchemas || {};
var PSHEMAS = DATA.processSchemas || {};
var PTIPS = DATA.processTips || {};
var WAVE_SIMPLE = DATA.waveSimpleFields || [];
var WAVE_RAWKEYS = DATA.waveRawKeys || [];
/* 掉落包候选池：植物+僵尸+额外僵尸+道具（礼盒/传送带可能掉任何包） */
var PKT_POOL = DATA.plant.concat(DATA.zombie, DATA.zombieExtra, DATA.item);

/* 单个规格字段 → 控件行；d 为 Data 对象；rerender 用于列表类编辑后整卡刷新 */
function schemaField(d, f, rerender){
  var tip = f.tip ? f.tip : ((f.def!==undefined && f.def!==null) ? ('游戏默认 '+f.def) : null);
  if(f.t === 'num'){
    return row(f.label+' ('+f.k+')',
      numInput(function(){return d[f.k];}, function(v){ if(v===null) delete d[f.k]; else d[f.k]=v; }, 'any'),
      tip);
  }
  if(f.t === 'bool'){
    var c = el('input',{type:'checkbox',style:'width:auto'});
    c.checked = (f.k in d) ? !!d[f.k] : !!f.def;
    c.addEventListener('change', function(){ d[f.k] = c.checked; });
    return row(f.label+' ('+f.k+')', el('div',{},[c]), tip);
  }
  if(f.t === 'text'){
    return row(f.label+' ('+f.k+')',
      txtInput(function(){return d[f.k];}, function(v){ if(v==='') delete d[f.k]; else d[f.k]=v; }),
      tip);
  }
  if(f.t === 'sel'){
    var opts = f.imp ? (resolveImport('import:'+f.imp)||[]) : normOpts(f.opts);
    return row(f.label+' ('+f.k+')',
      selInput(function(){return d[f.k];}, function(v){ if(v==='') delete d[f.k]; else d[f.k]=v; }, opts, !f.req),
      tip);
  }
  if(f.t === 'combo'){
    var copts = f.imp ? (resolveImport('import:'+f.imp)||[]) : normOpts(f.opts);
    return row(f.label+' ('+f.k+')',
      labelCombo(function(){return d[f.k];}, function(v){ if(v==='') delete d[f.k]; else d[f.k]=v; }, copts),
      tip);
  }
  if(f.t === 'enumint'){
    var eopt = (f.opts||[]).map(function(p){ return {label:p[0], value:String(p[1])}; });
    return row(f.label+' ('+f.k+')',
      selInput(function(){ return (d[f.k]===undefined||d[f.k]===null)?'':String(d[f.k]); },
               function(v){ if(v==='') delete d[f.k]; else d[f.k]=Number(v); }, eopt, true),
      tip);
  }
  if(f.t === 'plants'){
    d[f.k] = d[f.k] || [];
    return row(f.label+' ('+f.k+')',
      multiPicker(function(){return d[f.k]||[];}, function(v){ d[f.k]=v; }, DATA.plant));
  }
  if(f.t === 'pkts'){
    d[f.k] = d[f.k] || [];
    return row(f.label+' ('+f.k+')', packetWeightEditor(d, f.k, rerender));
  }
  if(f.t === 'slots'){
    d[f.k] = d[f.k] || [];
    return row(f.label+' ('+f.k+')', slotItemEditor(d, f.k, rerender));
  }
  if(f.t === 'prio'){
    d[f.k] = d[f.k] || [];
    return row(f.label+' ('+f.k+')', prioEditor(d, f.k, rerender));
  }
  if(f.t === 'prespawn'){
    d[f.k] = d[f.k] || [];
    return row(f.label+' ('+f.k+')', prespawnEditor(d, f.k, rerender));
  }
  if(f.t === 'vases'){
    d[f.k] = d[f.k] || [];
    return row(f.label+' ('+f.k+')', vaseEditor(d, f.k, rerender));
  }
  if(f.t === 'vasefill'){
    d[f.k] = d[f.k] || [];
    return row(f.label+' ('+f.k+')', vaseFillEditor(d, f.k, rerender));
  }
  if(f.t === 'rawkey'){
    var det = el('details',{});
    var sum = el('summary',{text:f.label+'（原始 JSON）'+((d[f.k]!==undefined)?'（已配置）':'')});
    sum.addEventListener('click', function(){ setTimeout(function(){
      ta.value = (d[f.k]===undefined||d[f.k]===null)?'':JSON.stringify(d[f.k],null,1); },0); });
    var ta = el('textarea',{style:'min-height:70px'});
    ta.value = (d[f.k]===undefined||d[f.k]===null)?'':JSON.stringify(d[f.k],null,1);
    ta.addEventListener('input', function(){
      var s = ta.value.trim();
      if(!s){ delete d[f.k]; ta.style.borderColor=''; refreshSummary(); return; }
      try{ d[f.k]=JSON.parse(s); ta.style.borderColor=''; refreshSummary(); }
      catch(e){ ta.style.borderColor='#f85149'; }
    });
    function refreshSummary(){
      sum.textContent = f.label+'（原始 JSON）'+((d[f.k]!==undefined)?'（已配置）':'');
    }
    det.appendChild(sum); det.appendChild(ta);
    return el('div',{},[det]);
  }
  return el('div',{});
}

/* 权重掉落包列表（RainMode / ConveyorBelt 的 Packet，元素出自
   TowerDefenseRainModePacketConfig / TowerDefenseConveyorPacketConfig）：
   {Name, Weight, MinNum(-1不限), MaxNum(-1不限), MinMagnification, MaxMagnification, Override?} */
function packetWeightEditor(d, key, rerender){
  var box = el('div',{});
  function numCell(obj, k, ph, w){
    var i = el('input',{type:'number',step:'any',style:'width:'+(w||'72px'),
      value:(obj[k]===undefined?'':obj[k]), placeholder:ph||''});
    i.addEventListener('input', function(){
      if(i.value==='') delete obj[k]; else obj[k]=Number(i.value);
    });
    return i;
  }
  function render(){
    box.innerHTML = '';
    var arr = d[key] || [];
    arr.forEach(function(p, i){
      var line = el('div',{style:'display:flex;gap:5px;align-items:center;flex-wrap:wrap;margin:4px 0'});
      line.appendChild(selInput(function(){return p.Name;}, function(v){p.Name=v;}, PKT_POOL, false));
      line.appendChild(numCell(p,'Weight','权重'));
      line.appendChild(numCell(p,'MinNum','最少'));
      line.appendChild(numCell(p,'MaxNum','最多'));
      line.appendChild(numCell(p,'MinMagnification','少倍率'));
      line.appendChild(numCell(p,'MaxMagnification','多倍率'));
      line.appendChild(el('button',{text:'↑',title:'上移',onclick:function(){
        if(i>0){ var t=arr[i-1]; arr[i-1]=p; arr[i]=t; render(); } }}));
      line.appendChild(el('button',{text:'↓',title:'下移',onclick:function(){
        if(i<arr.length-1){ var t=arr[i+1]; arr[i+1]=p; arr[i]=t; render(); } }}));
      line.appendChild(el('button',{class:'danger',text:'×',title:'删除',onclick:function(){
        arr.splice(i,1); if(!arr.length) delete d[key]; render(); }}));
      line.appendChild(packetOverrideEditor(p, render));
      box.appendChild(line);
    });
    box.appendChild(el('button',{text:'＋ 添加掉落包',onclick:function(){
      d[key] = d[key] || [];
      d[key].push({Name:(DATA.plant[0]||{}).value, Weight:10,
                   MinNum:-1, MaxNum:-1, MinMagnification:0, MaxMagnification:0});
      render(); }}));
  }
  render();
  return box;
}

/* 转盘卡池（SlotMachine.PacketList，元素为字符串，出自
   TowerDefenseBattleFeatureSlotMachine.ParseSlotItem :629-698）：
   - "卡牌名@权重"          → 卡牌奖励（权重省略=1）
   - "SUN:数量@权重"        → 阳光奖励（默认 25）
   - "BRAIN:数量@权重"      → 脑子阳光奖励（BRAINSUN/SUNBRAIN 等价，默认 25）
   - "DIAMOND:数量@权重"    → 钻石奖励（默认 1）
   - "COIN:数量@权重"       → 金币奖励（默认 1000） */
var SLOT_TYPES = [
  {value: 'packet',  label: '卡牌'},
  {value: 'SUN',     label: '阳光 SUN'},
  {value: 'BRAIN',   label: '脑子阳光 BRAIN'},
  {value: 'DIAMOND', label: '钻石 DIAMOND'},
  {value: 'COIN',    label: '金币 COIN'}
];
function parseSlotItem(raw){
  var s = String(raw === undefined || raw === null ? '' : raw).trim();
  var w = 1, body = s;
  var at = s.lastIndexOf('@');
  if(at >= 0){
    var tail = Number(s.slice(at + 1).trim());
    if(tail > 0) w = tail;
    body = s.slice(0, at).trim();
  }
  var parts = body.split(':').map(function(x){ return x.trim(); }).filter(function(x){ return x !== ''; });
  var head = (parts[0] || '').toUpperCase();
  if(head === 'SUN' || head === 'BRAIN' || head === 'BRAINSUN' || head === 'SUNBRAIN' ||
     head === 'DIAMOND' || head === 'COIN'){
    return {type: head === 'SUN' ? 'SUN' : (head === 'DIAMOND' ? 'DIAMOND' : (head === 'COIN' ? 'COIN' : 'BRAIN')),
            packet: '', amount: (Number(parts[1]) > 0 ? Number(parts[1]) : null), weight: w};
  }
  return {type: 'packet',
          packet: (parts.length === 2 && Number(parts[1]) > 0 ? parts[0] : body),
          amount: null, weight: (parts.length === 2 && Number(parts[1]) > 0 ? Number(parts[1]) : w)};
}
function encodeSlotItem(o){
  var body = o.type === 'packet' ? (o.packet || '')
           : o.type + ':' + (o.amount > 0 ? o.amount : 0);
  return body + '@' + (o.weight > 0 ? o.weight : 1);
}
function slotItemEditor(d, key, rerender){
  var box = el('div',{});
  function render(){
    box.innerHTML = '';
    var arr = d[key] || [];
    arr.forEach(function(raw, i){
      var st = parseSlotItem(raw);
      var line = el('div',{style:'display:flex;gap:5px;align-items:center;flex-wrap:wrap;margin:4px 0'});
      line.appendChild(el('span',{class:'hint',text:(i+1)+'.',style:'width:24px'}));
      line.appendChild(selInput(function(){ return st.type; }, function(v){
        st.type = v; arr[i] = encodeSlotItem(st); render(); }, SLOT_TYPES, false));
      if(st.type === 'packet'){
        line.appendChild(selInput(function(){ return st.packet; }, function(v){
          st.packet = v; arr[i] = encodeSlotItem(st); }, PKT_POOL, false));
      } else {
        var amt = el('input',{type:'number',step:'1',style:'width:90px',
          placeholder:'数量', value:(st.amount===null?'':st.amount),
          title: st.type==='SUN'?'默认25':(st.type==='BRAIN'?'默认25':(st.type==='DIAMOND'?'默认1':'默认1000'))});
        amt.addEventListener('input', function(){
          st.amount = amt.value===''?null:Number(amt.value);
          arr[i] = encodeSlotItem(st);
        });
        line.appendChild(amt);
      }
      var wt = el('input',{type:'number',step:'1',style:'width:70px',placeholder:'权重',
        value:st.weight, title:'权重（≥1，越大越容易转到）'});
      wt.addEventListener('input', function(){
        st.weight = Number(wt.value||1);
        arr[i] = encodeSlotItem(st);
      });
      line.appendChild(wt);
      line.appendChild(el('button',{text:'↑',title:'上移',onclick:function(){
        if(i>0){ var t=arr[i-1]; arr[i-1]=arr[i]; arr[i]=t; render(); } }}));
      line.appendChild(el('button',{text:'↓',title:'下移',onclick:function(){
        if(i<arr.length-1){ var t=arr[i+1]; arr[i+1]=arr[i]; arr[i]=t; render(); } }}));
      line.appendChild(el('button',{class:'danger',text:'×',title:'删除',onclick:function(){
        arr.splice(i,1); if(!arr.length) delete d[key]; render(); }}));
      box.appendChild(line);
    });
    box.appendChild(el('button',{text:'＋ 添加转盘项',onclick:function(){
      d[key] = d[key] || [];
      d[key].push(encodeSlotItem({type:'packet', packet:(DATA.plant[0]||{}).value, weight:10}));
      render(); }}));
  }
  render();
  return box;
}

/* 优先发包列表（ConveyorBelt.PacketPrioritySpawnList）：
   元素为字符串或 {PacketName, Override}，按顺序优先消耗 */
function prioEditor(d, key, rerender){
  var box = el('div',{});
  function render(){
    box.innerHTML = '';
    var arr = d[key] || [];
    arr.forEach(function(p, i){
      var isObj = (typeof p === 'object' && p !== null);
      var line = el('div',{style:'display:flex;gap:5px;align-items:center;margin:4px 0'});
      var idx = el('span',{class:'hint',text:(i+1)+'.',style:'width:24px'});
      line.appendChild(idx);
      line.appendChild(selInput(
        function(){ return isObj ? p.PacketName : p; },
        function(v){ if(isObj) p.PacketName=v; else arr[i]=v; },
        PKT_POOL, false));
      line.appendChild(el('button',{class:'danger',text:'×',onclick:function(){
        arr.splice(i,1); if(!arr.length) delete d[key]; render(); }}));
      box.appendChild(line);
      if(isObj && p.Override !== undefined){
        box.appendChild(row('Override', rawJsonCtl(function(){return p.Override;},
          function(v){ if(v) p.Override=v; else delete p.Override; })));
      }
      if(isObj && p.Override === undefined){
        box.appendChild(el('div',{},[el('button',{text:'＋ 覆盖 Override',onclick:function(){
          p.Override={}; render(); }})]));
      }
      if(!isObj){
        box.appendChild(el('div',{},[el('button',{text:'＋ 转为对象(加Override)',onclick:function(){
          arr[i] = {PacketName:p}; render(); }})]));
      }
    });
    box.appendChild(el('button',{text:'＋ 添加优先包',onclick:function(){
      d[key] = d[key] || [];
      d[key].push((DATA.plant[0]||{}).value);
      render(); }}));
  }
  render();
  return box;
}

/* 预种植列表（PreSpawn.Packet，元素 TowerDefenseLevelPreSpawnConfig）：
   {Name, GridPos:[x,y], CharacterOverride?} */
function prespawnEditor(d, key, rerender){
  var box = el('div',{});
  function render(){
    box.innerHTML = '';
    var arr = d[key] || [];
    arr.forEach(function(p, i){
      var card = el('div',{class:'card'});
      card.appendChild(el('div',{class:'hd'},[
        el('span',{class:'ttl',text:'预种植 '+(i+1)}),
        el('span',{class:'sp'}),
        el('button',{class:'danger',text:'删除',onclick:function(){
          arr.splice(i,1); if(!arr.length) delete d[key]; render(); }})
      ]));
      var line = el('div',{class:'row'},[el('label',{text:'卡牌 / 格位',style:'width:110px'})]);
      var ctl = el('div',{class:'ctl',style:'display:flex;gap:5px'});
      ctl.appendChild(selInput(function(){return p.Name;}, function(v){p.Name=v;}, PKT_POOL, false));
      var gx = el('input',{type:'number',style:'width:70px',placeholder:'列x',
        value:(p.GridPos&&p.GridPos[0]!==undefined?p.GridPos[0]:0)});
      var gy = el('input',{type:'number',style:'width:70px',placeholder:'行y',
        value:(p.GridPos&&p.GridPos[1]!==undefined?p.GridPos[1]:0)});
      function updG(){ p.GridPos = [Number(gx.value||0), Number(gy.value||0)]; }
      gx.addEventListener('input',updG); gy.addEventListener('input',updG);
      ctl.appendChild(gx); ctl.appendChild(gy);
      line.appendChild(ctl);
      card.appendChild(line);
      var ovrWrap = el('div',{});
      function renderOvr(){
        ovrWrap.innerHTML = '';
        if(p.CharacterOverride){
          ovrWrap.appendChild(overrideEditor(p.CharacterOverride, '预种植覆盖 CharacterOverride', {mode:'plant'}));
          ovrWrap.appendChild(el('button',{class:'danger',text:'移除覆盖',onclick:function(){
            delete p.CharacterOverride; renderOvr(); }}));
        }else{
          ovrWrap.appendChild(el('button',{text:'＋ 添加角色覆盖',onclick:function(){
            p.CharacterOverride = {}; renderOvr(); }}));
        }
      }
      renderOvr();
      card.appendChild(el('details',{},[el('summary',{text:'角色覆盖 Override'+(p.CharacterOverride?'（已配置）':'')}), ovrWrap]));
      box.appendChild(card);
    });
    box.appendChild(el('button',{text:'＋ 添加预种植',onclick:function(){
      d[key] = d[key] || [];
      d[key].push({Name:(DATA.plant[0]||{}).value, GridPos:[0,0]});
      render(); }}));
  }
  render();
  return box;
}

/* 花瓶列表（Process Vase.Vase，元素 TowerDefenseLevelVaseConfig）：
   {PacketName, Type, GridPos:[x,y], Override?} */
function vaseEditor(d, key, rerender){
  var box = el('div',{});
  function render(){
    box.innerHTML = '';
    var arr = d[key] || [];
    arr.forEach(function(p, i){
      var line = el('div',{style:'display:flex;gap:5px;align-items:center;flex-wrap:wrap;margin:4px 0'});
      line.appendChild(selInput(function(){return p.PacketName;}, function(v){p.PacketName=v;}, PKT_POOL, false));
      var ty = el('input',{type:'text',style:'width:80px',placeholder:'Type', value:val(p.Type,'Normal')});
      ty.addEventListener('input', function(){ p.Type = ty.value; });
      line.appendChild(ty);
      var gx = el('input',{type:'number',style:'width:64px',placeholder:'x',
        value:(p.GridPos&&p.GridPos[0]!==undefined?p.GridPos[0]:0)});
      var gy = el('input',{type:'number',style:'width:64px',placeholder:'y',
        value:(p.GridPos&&p.GridPos[1]!==undefined?p.GridPos[1]:0)});
      function updG(){ p.GridPos = [Number(gx.value||0), Number(gy.value||0)]; }
      gx.addEventListener('input',updG); gy.addEventListener('input',updG);
      line.appendChild(gx); line.appendChild(gy);
      line.appendChild(el('button',{class:'danger',text:'×',onclick:function(){
        arr.splice(i,1); if(!arr.length) delete d[key]; render(); }}));
      box.appendChild(line);
      if(p.Override !== undefined){
        box.appendChild(row('Override', rawJsonCtl(function(){return p.Override;},
          function(v){ if(v) p.Override=v; else delete p.Override; })));
      }
    });
    box.appendChild(el('button',{text:'＋ 添加花瓶',onclick:function(){
      d[key] = d[key] || [];
      d[key].push({PacketName:'', Type:'Normal', GridPos:[0,0]});
      render(); }}));
  }
  render();
  return box;
}

/* 填瓶列表（Process Vase.VaseFill，元素 TowerDefenseLevelVaseFillConfig）：
   {PacketName, Override?} */
function vaseFillEditor(d, key, rerender){
  var box = el('div',{});
  function render(){
    box.innerHTML = '';
    var arr = d[key] || [];
    arr.forEach(function(p, i){
      var line = el('div',{style:'display:flex;gap:5px;align-items:center;margin:4px 0'});
      line.appendChild(el('span',{class:'hint',text:(i+1)+'.',style:'width:24px'}));
      line.appendChild(selInput(function(){return p.PacketName;}, function(v){p.PacketName=v;}, PKT_POOL, false));
      line.appendChild(el('button',{class:'danger',text:'×',onclick:function(){
        arr.splice(i,1); if(!arr.length) delete d[key]; render(); }}));
      box.appendChild(line);
    });
    box.appendChild(el('button',{text:'＋ 添加填瓶',onclick:function(){
      d[key] = d[key] || [];
      d[key].push({PacketName:(DATA.plant[0]||{}).value});
      render(); }}));
  }
  render();
  return box;
}

/* ---------- 事件（沿用原构建器事件表；Value 为「具名键对象」而非数组） ---------- */
function EVENTS_BY(kind){
  return DATA.event.filter(function(e){ return (e.class||[]).indexOf(kind)>=0; });
}
function EVENT_DEF(name){
  return DATA.event.filter(function(e){ return e.value===name; })[0] || null;
}
/* 单个事件参数控件（9 种类型） */
function paramControl(def, get, set){
  var ty = def.type, cur = get();
  if(ty === 'constant'){
    return el('input',{type:'text', readonly:'readonly',
      value:String(def.constValue===undefined?'':def.constValue),
      style:'background:#1a1d23;color:#9aa3b2'});
  }
  if(ty === 'boolean'){
    var b = el('input',{type:'checkbox',style:'width:auto'});
    b.checked = (cur===undefined||cur===null) ? !!def.default : !!cur;
    b.addEventListener('change', function(){ set(b.checked); });
    return el('div',{},[b]);
  }
  if(ty === 'number' || ty === 'range-number'){
    var n = el('input',{type:'number', step:def.step||'any',
      value:(cur===undefined||cur===null?'':cur), placeholder:(def.default!==undefined?String(def.default):'')});
    n.addEventListener('input', function(){ set(n.value===''?null:Number(n.value)); });
    return n;
  }
  if(ty === 'select'){
    return selInput(get, set, resolveImport(def.options)||[], true);
  }
  if(ty === 'select-pool'){
    if(!Array.isArray(cur)) set([]);
    return multiPicker(function(){ return get()||[]; }, set, resolveImport(def.options)||[]);
  }
  if(ty === 'region'){
    var r = cur || {}, box = el('div',{style:'display:flex;gap:5px'});
    ['x','y','z','w'].forEach(function(k){
      var i = el('input',{type:'number',step:'any',value:(r[k]===undefined?'':r[k]),placeholder:k});
      i.addEventListener('input', function(){
        var o = get()||{};
        if(i.value==='') delete o[k]; else o[k]=Number(i.value);
        set(o);
      });
      box.appendChild(i);
    });
    return box;
  }
  if(ty === 'attributes'){
    var holder = el('div',{});
    function drawAttr(){
      holder.innerHTML='';
      var v = get();
      if(v === undefined || v === null){
        holder.appendChild(el('button',{text:'＋ 配置覆盖（'+(def.classType||'character')+'）',
          onclick:function(){ set({}); drawAttr(); }}));
      }else{
        holder.appendChild(el('button',{class:'danger',text:'✕ 清除覆盖',onclick:function(){ set(undefined); drawAttr(); }}));
        holder.appendChild(def.classType === 'card'
          ? cardOverrideFields(v)
          : overrideEditor(v, def.label||'角色覆盖', {mode:'plant'}));
      }
    }
    drawAttr();
    return holder;
  }
  var ti = el('input',{type:'text', placeholder:(def.default!==undefined?String(def.default):''),
    value:(cur===undefined||cur===null?'':cur)});
  ti.addEventListener('input', function(){ set(ti.value); });
  return ti;
}
/* 事件列表编辑器：arrRef 由调用方用 getArr/setArr 读写，空数组则删除该键 */
function eventListEditor(getArr, setArr, kind){
  var box = el('div',{});
  function render(){
    box.innerHTML = '';
    var arr = getArr() || [];
    var addSel = el('select',{});
    addSel.appendChild(el('option',{value:'',text:'＋ 添加'+(kind==='SpawnEvent'?'生成':'死亡')+'事件…'}));
    EVENTS_BY(kind).forEach(function(e){
      addSel.appendChild(el('option',{value:e.value,text:e.label+' ('+e.value+')'}));
    });
    addSel.addEventListener('change', function(){
      if(!addSel.value) return;
      var ev = {EventName:addSel.value, Value:{}};
      var d0 = EVENT_DEF(addSel.value);
      if(d0) (d0.properties||[]).forEach(function(pd){
        if(pd.type === 'constant') ev.Value[pd.value] = pd.constValue;
      });
      arr.push(ev); setArr(arr); render();
    });
    box.appendChild(addSel);

    arr.forEach(function(ev, i){
      var def = EVENT_DEF(ev.EventName);
      var card = el('div',{class:'card'},[
        el('div',{class:'hd'},[
          el('span',{class:'ttl',text:(def?def.label:ev.EventName)+' ('+ev.EventName+')'}),
          el('span',{class:'sp'}),
          el('button',{text:'↑',title:'上移',onclick:function(){
            if(i>0){ var t=arr[i-1]; arr[i-1]=ev; arr[i]=t; setArr(arr); render(); } }}),
          el('button',{text:'↓',title:'下移',onclick:function(){
            if(i<arr.length-1){ var t=arr[i+1]; arr[i+1]=ev; arr[i]=t; setArr(arr); render(); } }}),
          el('button',{class:'danger',text:'删除',onclick:function(){
            arr.splice(i,1); setArr(arr); render(); }})
        ])
      ]);
      ev.Value = ev.Value || {};
      var pds = def ? (def.properties||[]) : [];
      pds.forEach(function(pd){
        var ctl = paramControl(pd,
          function(){ return ev.Value[pd.value]; },
          function(v){ if(v===undefined) delete ev.Value[pd.value]; else ev.Value[pd.value]=v; });
        if(pd.type === 'attributes'){
          /* 嵌套覆盖：全宽纵向展开在下方，避免挤在 .row>.ctl 右侧导致无法编辑 */
          card.appendChild(stackBlock(pd.label+' ('+pd.value+')', ctl,
            el('span',{class:'hint',text:'嵌套覆盖 classType='+(pd.classType||'-')})));
        }else{
          card.appendChild(row(pd.label+' ('+pd.value+')', ctl,
            pd.type==='constant' ? '固定值，不可编辑'
              : (def && def.display ? def.display : null)));
        }
      });
      if(!def){
        var t = el('textarea',{});
        t.value = JSON.stringify(ev.Value,null,1);
        t.addEventListener('input', function(){
          try{ ev.Value=JSON.parse(t.value||'{}'); t.style.borderColor=''; }
          catch(e){ t.style.borderColor='#f85149'; }
        });
        card.appendChild(row('Value（未登记事件，原始 JSON）', t));
      }
      box.appendChild(card);
    });
  }
  render();
  return box;
}

/* ---------- 状态 ---------- */
var LV = null;
/* 往返无损标记：导入时记录原文件是否带 Feature / Process 顶层键，
   导出时若原本没有且编辑后仍为空，则不写出该键（不污染纯扁平格式关卡） */
var RAWFLAGS = {feature: true, process: true};
function feat(n){ var f=(LV.Feature||[]).filter(function(x){return x.Name===n;})[0]; return f||null; }
function fd(n){ var f=feat(n); return f?f.Data:null; }
function ensureFeat(n){
  var f = feat(n);
  if(!f){ f = {Name:n, Data:{}}; LV.Feature.push(f); }
  return f.Data;
}

/* ---------- 属性覆盖编辑器（TowerDefenseCharacterOverride） ---------- */
/* 覆盖字段由原构建器 attribute 表推导（排除 *Card 与 attributes 容器），
   保证「植物 / 僵尸 / 其它」按 class 自动过滤，且与官方定义同源 */
var CHAR_CLASSES = ['plant','zombie','other','ball','item'];
var OVR_FIELDS = DATA.attribute.filter(function(a){
  if((a.property||{}).type === 'attributes') return false;  // CharacterOverride 是容器
  return (a.class||[]).some(function(c){ return CHAR_CLASSES.indexOf(c)>=0; });
}).map(function(a){
  var ty = (a.property||{}).type;
  return {
    key: a.value, label: a.label, cls: a.class,
    type: ty==='armor-check-select' ? 'armor'
        : ty==='event-table'        ? 'events'
        : ty==='range-number'       ? 'vec2'
        : ty==='number'             ? 'num'
        : 'bool'
  };
});
function unitClassOf(uid){
  if(!uid) return '';
  function has(list){ return (list||[]).some(function(o){ return o.value===uid; }); }
  if(has(DATA.plant)) return 'plant';
  if(has(DATA.zombie) || has(DATA.zombieExtra)) return 'zombie';
  if(has(DATA.ball)) return 'ball';
  if(has(DATA.item)) return 'other';
  return '';
}
function overrideEditor(obj, title, opts){
  opts = opts || {};
  var mode = opts.mode || 'zombie';   // 'zombie' | 'plant'
  var box = el('div',{class:'card'});
  var unitSel = el('select',{style:'width:auto'});
  if(opts.lockUid){
    unitSel.appendChild(el('option',{value:opts.lockUid,text:opts.lockUid}));
    unitSel.value = opts.lockUid;
    unitSel.disabled = true;
  }else{
    unitSel.appendChild(el('option',{value:'',text:'按单位过滤属性（可选）…'}));
    var pool = (mode==='plant') ? DATA.plant
             : DATA.zombie.concat(DATA.zombieExtra, DATA.plant, DATA.item);
    pool.forEach(function(o){
      unitSel.appendChild(el('option',{value:o.value,text:o.label+' ('+o.value+')'}));
    });
    if(opts.uid) unitSel.value = opts.uid;   // 预选（未锁定，可改）
  }
  box.appendChild(el('div',{class:'hd'},[el('span',{class:'ttl',text:title}), el('span',{class:'sp'}), unitSel]));

  var body = el('div',{});
  box.appendChild(body);

  function renderBody(){
    body.innerHTML = '';
    var uid = unitSel.value;
    var ucls = unitClassOf(uid);
    var fields = OVR_FIELDS.filter(function(f){
      return !ucls || f.cls.indexOf(ucls)>=0;
    });
    fields.forEach(function(f){
      var cur = obj[f.key];
      var ctl, tip = null;
      if(f.type==='bool'){
        var c = el('input',{type:'checkbox',style:'width:auto'});
        c.checked = (cur===true);
        c.addEventListener('change',function(){
          if(c.checked) obj[f.key]=true; else delete obj[f.key];
        });
        ctl = el('div',{},[c]);
        tip = '勾选=写入 true；取消勾选=不写入该键';
      } else if(f.type==='num'){
        var i = el('input',{type:'number',step:'any',value:(cur===undefined?'':cur)});
        i.addEventListener('input',function(){
          if(i.value==='') delete obj[f.key]; else obj[f.key]=Number(i.value);
        });
        ctl = i; tip = '留空 = 不写入（游戏中取默认值 -1）';
      } else if(f.type==='vec2'){
        var a = el('input',{type:'number',step:'any',style:'width:48%;display:inline-block',
                  placeholder:'最小', value:(cur&&cur[0]!==undefined?cur[0]:'')});
        var b = el('input',{type:'number',step:'any',style:'width:48%;display:inline-block',
                  placeholder:'最大', value:(cur&&cur[1]!==undefined?cur[1]:'')});
        function upd(){
          var x = a.value===''? -1:Number(a.value), y = b.value===''? -1:Number(b.value);
          if(a.value==='' && b.value==='') delete obj[f.key]; else obj[f.key]=[x,y];
        }
        a.addEventListener('input',upd); b.addEventListener('input',upd);
        ctl = el('div',{},[a,b]); tip = '区间 [最小, 最大]，留空 = 不写入';
      } else if(f.type==='armor'){
        var armorOpts = DATA.armor.slice();
        if(uid){
          armorOpts = armorOpts.filter(function(x){ return (DATA.armorWls[x.wl]||[]).indexOf(uid)>=0; });
        }
        ctl = multiPicker(function(){ return obj[f.key] || []; },
          function(v){ if(v.length) obj[f.key]=v; else delete obj[f.key]; },
          armorOpts.map(function(x){ return {label:x.label+' (槽位'+x.slot+')', value:x.value}; }));
        tip = uid? ('已按单位过滤：'+armorOpts.length+' 项可用') : ('共 '+DATA.armor.length+' 项');
      } else if(f.type==='events'){
        ctl = eventListEditor(
          function(){ return obj[f.key]; },
          function(v){ if(v && v.length) obj[f.key]=v; else delete obj[f.key]; },
          f.key);
        tip = '事件按顺序执行，可用 ↑↓ 调整';
      }
      body.appendChild(row(f.label+' ('+f.key+')', ctl, tip));
    });
    if(!fields.length) body.appendChild(el('div',{class:'hint',
      text:'该单位类型没有可用的覆盖字段。'}));

    /* PropertyChange：whitelist 过滤 + ka() 去重 */
    var props = uid ? PROPS_ALL.filter(function(p){ return (p.whitelist||[]).indexOf(uid)>=0; })
                    : PROPS_ALL;
    var pc = el('div',{});
    /* ⚠️ 惰性初始化：renderPC() 末尾会在「空」时 delete obj.PropertyChange（保证导出不带
       "PropertyChange":[] 噪声），因此所有「添加」型 handler 必须先用 ensurePC() 重建数组，
       否则从空状态添加会 undefined.push 抛错（UI 毫无反应）。 */
    function ensurePC(){
      if(!Array.isArray(obj.PropertyChange)) obj.PropertyChange = [];
      return obj.PropertyChange;
    }
    function renderPC(){
      pc.innerHTML = '';
      obj.PropertyChange = obj.PropertyChange || [];

      /* 添加方式①：单选下拉 → 选中即刻在下方生成一个编辑框 */
      var quickSel = el('select',{style:'width:auto;max-width:330px'});
      quickSel.appendChild(el('option',{value:'',text:'＋ 选择一个属性，立即在下方生成编辑框…'}));
      props.forEach(function(p){
        if(obj.PropertyChange.some(function(x){return x.PropertyName===p.value;})) return;
        quickSel.appendChild(el('option',{value:p.value,text:p.label+' ('+p.value+')'}));
      });
      quickSel.addEventListener('change', function(){
        if(!quickSel.value) return;
        ensurePC().push({PropertyName:quickSel.value, Value:null});
        renderPC();
      });
      pc.appendChild(row('属性覆盖 PropertyChange（单选即出框）', quickSel,
        '选一个属性 → 下方立即生成一个框让你编写「值」（与死亡/生成事件里的用法一致）'));

      /* 添加方式②：勾选批量加入 */
      var checklist = propChecklist(props,
        function(v){ return (obj.PropertyChange||[]).some(function(x){return x.PropertyName===v;}); },
        function(picked){
          var arr = ensurePC();
          picked.forEach(function(v){ arr.push({PropertyName:v, Value:null}); });
          renderPC();
        });
      pc.appendChild(row('属性覆盖 PropertyChange（勾选批量加入）', checklist,
        (uid? '已按 whitelist 过滤：'+props.length+' 项可用' : '未过滤：共 '+props.length+' 项')
        +'；已加入 '+obj.PropertyChange.length+' 条，可在下方逐条编辑「值」'));
      var addRow = el('div',{style:'display:flex;gap:6px;align-items:center;flex-wrap:wrap'});
      var cName = el('input',{type:'text',placeholder:'自定义属性名…',style:'max-width:190px'});
      var cType = el('select',{style:'width:auto'});
      [['number','数字'],['text','文本'],['boolean','布尔'],['json','JSON']].forEach(function(t){
        cType.appendChild(el('option',{value:t[0],text:t[1]}));
      });
      var cBtn = el('button',{text:'＋ 自定义',onclick:function(){
        var nm = (cName.value||'').trim();
        if(!nm){ alert('请输入属性名'); return; }
        var arr = ensurePC();
        if(arr.some(function(x){return x.PropertyName===nm;})){
          alert('属性「'+nm+'」已存在'); return;
        }
        var ty = cType.value;
        arr.push({PropertyName:nm,
          Value: ty==='number'?0 : ty==='text'?'' : ty==='boolean'?false : null});
        renderPC();
      }});
      addRow.appendChild(cName); addRow.appendChild(cType); addRow.appendChild(cBtn);
      pc.appendChild(row('自定义属性', addRow, '不在预设里的属性名可直接输入，类型可选'));

      obj.PropertyChange.forEach(function(entry, i){
        var p = PROPS_ALL.filter(function(x){return x.value===entry.PropertyName;})[0];
        var ctl, note = '';
        if(p && p.type === 'select'){
          ctl = selInput(function(){ return entry.Value; },
                         function(v){ entry.Value=v; }, resolveImport(p.options)||[], true);
        } else if(p && p.type === 'select-pool'){
          if(!Array.isArray(entry.Value)) entry.Value=[];
          ctl = multiPicker(function(){ return entry.Value||[]; },
                            function(v){ entry.Value=v; }, resolveImport(p.options)||[]);
        } else if(p && (p.type==='int'||p.type==='float'||p.type==='double')){
          var inp = el('input',{type:'number',step:'any',
            value:(entry.Value===null||entry.Value===undefined?'':entry.Value)});
          inp.addEventListener('input',function(){
            entry.Value = inp.value===''? null : Number(inp.value);
          });
          ctl = inp;
        } else if(typeof entry.Value === 'boolean'){
          var cb = el('input',{type:'checkbox',style:'width:auto'});
          cb.checked = entry.Value;
          cb.addEventListener('change', function(){ entry.Value = cb.checked; });
          ctl = el('div',{},[cb]);
        } else if(typeof entry.Value === 'string'){
          var si = el('input',{type:'text', value:entry.Value});
          si.addEventListener('input', function(){ entry.Value = si.value; });
          ctl = si;
        } else if(typeof entry.Value === 'number'){
          var ni = el('input',{type:'number',step:'any', value:entry.Value});
          ni.addEventListener('input', function(){
            entry.Value = ni.value===''? null : Number(ni.value);
          });
          ctl = ni;
        } else {
          ctl = rawJsonCtl(function(){ return entry.Value; },
                           function(v){ entry.Value = v; });
          note = '（原始 JSON）';
        }
        var c = el('div',{class:'card'},[
          el('div',{class:'hd'},[
            el('span',{class:'ttl',
              text:(p?p.label:'(自定义)')+' ('+entry.PropertyName+')'+note}),
            el('span',{class:'sp'}),
            el('button',{class:'danger',text:'移除',onclick:function(){
              obj.PropertyChange.splice(i,1); renderPC(); }})
          ]),
          el('div',{class:'row'},[el('label',{text:'值',style:'width:60px'}),
                                  el('div',{class:'ctl'},[ctl])])
        ]);
        pc.appendChild(c);
      });
      if(!obj.PropertyChange.length) delete obj.PropertyChange;
    }
    renderPC();
    body.appendChild(pc);
  }
  unitSel.addEventListener('change', renderBody);
  renderBody();
  return box;
}

/* ---------- 波次编辑器 ---------- */
function waveEditor(){
  var d = fd('Wave') || ensureFeat('Wave');
  var wraps = [];
  var zopts = DATA.zombie.concat(DATA.zombieExtra);
  WAVE_SIMPLE.forEach(function(f){ wraps.push(schemaField(d, f)); });
  /* Survival / CustomSurvival / Dynamic：生存与动态难度，官方多为 {} 或数组，原始 JSON 编辑 */
  WAVE_RAWKEYS.forEach(function(f){
    wraps.push(schemaField(d, {k:f.k, label:f.label, t:'rawkey'}));
  });
  /* 全局出怪覆盖：惰性创建（未添加时完全不写入，避免空对象污染导出） */
  var gWrap = el('div',{});
  function renderGlobalOvr(){
    gWrap.innerHTML = '';
    if(d.SpawnOverride){
      gWrap.appendChild(overrideEditor(d.SpawnOverride, '全局出怪覆盖 SpawnOverride', {mode:'zombie'}));
      gWrap.appendChild(el('div',{class:'hint',
        text:'对该关所有出怪生效（游戏侧 TowerDefenseCharacterOverride）'}));
      gWrap.appendChild(el('button',{class:'danger',text:'移除全局覆盖',onclick:function(){
        delete d.SpawnOverride; renderGlobalOvr(); }}));
    }else{
      gWrap.appendChild(el('button',{text:'＋ 添加全局出怪覆盖 SpawnOverride',onclick:function(){
        d.SpawnOverride = {}; renderGlobalOvr(); }}));
    }
  }
  renderGlobalOvr();
  wraps.push(gWrap);

  d.Wave = d.Wave || [];
  var wbox = el('div',{});
  function renderWaves(){
    wbox.innerHTML = '';
    d.Wave.forEach(function(w, wi){
      w.Spawn = w.Spawn || []; w.Event = w.Event || [];
      if(!w.DynamicPlantfood) w.DynamicPlantfood = [0,0,0,0,0,0,0];
      var c = el('div',{class:'card'},[
        el('div',{class:'hd'},[
          el('span',{class:'ttl',text:'第 '+(wi+1)+' 波'}),
          el('span',{class:'sp'}),
          el('button',{text:'上移',onclick:function(){ if(wi>0){ var t=d.Wave[wi-1]; d.Wave[wi-1]=w; d.Wave[wi]=t; renderWaves(); } }}),
          el('button',{text:'下移',onclick:function(){ if(wi<d.Wave.length-1){ var t=d.Wave[wi+1]; d.Wave[wi+1]=w; d.Wave[wi]=t; renderWaves(); } }}),
          el('button',{text:'复制',onclick:function(){ d.Wave.splice(wi+1,0,JSON.parse(JSON.stringify(w))); renderWaves(); }}),
          el('button',{class:'danger',text:'删除',onclick:function(){ d.Wave.splice(wi,1); renderWaves(); }})
        ])
      ]);
      /* Spawn */
      var sbox = el('div',{});
      function renderSpawn(){
        sbox.innerHTML = '';
        w.Spawn.forEach(function(s, si){
          var sc = el('div',{class:'card'});
          sc.appendChild(el('div',{class:'row'},[
            el('label',{text:'出怪 '+(si+1),style:'width:70px'}),
            el('div',{class:'ctl'},[el('div',{style:'display:flex;gap:6px'},[
              selInput(function(){return s.Zombie;}, function(v){s.Zombie=v;}, zopts, false),
              el('input',{type:'number',value:val(s.Line,-1),style:'width:80px',title:'Line',
                oninput:function(e){ s.Line=Number(e.target.value); }}),
              el('input',{type:'number',value:val(s.Num,1),style:'width:80px',title:'Num',
                oninput:function(e){ s.Num=Number(e.target.value); }}),
              el('button',{class:'danger',text:'×',style:'width:38px',onclick:function(){
                w.Spawn.splice(si,1); renderSpawn(); }})
            ])])
          ]));
          /* 每条 Spawn 独立的生成 / 死亡事件（TowerDefenseLevelSpawnConfig） */
          sc.appendChild(el('details',{},[
            el('summary',{text:'生成事件 SpawnEvent（'+((s.SpawnEvent||[]).length)+' 条）'}),
            eventListEditor(function(){ return s.SpawnEvent; },
              function(v){ if(v && v.length) s.SpawnEvent=v; else delete s.SpawnEvent; },
              'SpawnEvent')
          ]));
          sc.appendChild(el('details',{},[
            el('summary',{text:'死亡事件 DieEvent（'+((s.DieEvent||[]).length)+' 条）'}),
            eventListEditor(function(){ return s.DieEvent; },
              function(v){ if(v && v.length) s.DieEvent=v; else delete s.DieEvent; },
              'DieEvent')
          ]));
          /* 每条 Spawn 独立覆盖（惰性创建，避免空对象污染导出） */
          var ovrWrap = el('div',{});
          function renderOvr(){
            ovrWrap.innerHTML = '';
            if(s.Override){
              ovrWrap.appendChild(overrideEditor(s.Override, '本条出怪覆盖 Override',
                {mode:'zombie', uid:s.Zombie}));
              ovrWrap.appendChild(el('button',{class:'danger',text:'移除本条覆盖',
                onclick:function(){ delete s.Override; renderOvr(); }}));
            }else{
              ovrWrap.appendChild(el('button',{text:'＋ 添加本条独立覆盖',
                onclick:function(){ s.Override = {}; renderOvr(); }}));
            }
          }
          renderOvr();
          sc.appendChild(el('details',{},[
            el('summary',{text:'独立覆盖 Override'+(s.Override?'（已配置）':'')}), ovrWrap]));
          sbox.appendChild(sc);
        });
        sbox.appendChild(el('button',{text:'＋ 添加出怪',onclick:function(){
          w.Spawn.push({Zombie:(zopts[0]||{}).value, Line:-1, Num:1}); renderSpawn(); }}));
      }
      renderSpawn();
      c.appendChild(el('div',{},[
        el('div',{class:'hint',text:'Spawn（Zombie / Line / Num）；每条可独立配置 Override / SpawnEvent / DieEvent'}),
        sbox]));

      /* DynamicPlantfood */
      var dp = el('input',{type:'text', value:(w.DynamicPlantfood||[]).join(', ')});
      dp.addEventListener('change', function(){
        w.DynamicPlantfood = dp.value.split(',').map(function(x){
          var n = Number(String(x).trim()); return isNaN(n)?0:n; });
      });
      c.appendChild(row('DynamicPlantfood', dp, '7 个数字，逗号分隔'));

      /* Event / GridSpawn / Dynamic：原始 JSON 高级编辑 */
      ['Event','GridSpawn'].forEach(function(k){
        var t = el('textarea',{});
        t.value = (w[k]&&w[k].length)?JSON.stringify(w[k],null,1):'';
        t.addEventListener('input',function(){
          var s=t.value.trim();
          if(!s){ delete w[k]; t.style.borderColor=''; return; }
          try{ w[k]=JSON.parse(s); t.style.borderColor=''; }
          catch(e){ t.style.borderColor='#f85149'; }
        });
        var det = el('details',{},[el('summary',{text:'高级：'+k+'（原始 JSON）'}), t]);
        c.appendChild(det);
      });
      var tdyn = el('textarea',{});
      tdyn.value = (w.Dynamic&&Object.keys(w.Dynamic).length)?JSON.stringify(w.Dynamic,null,1):'';
      tdyn.addEventListener('input',function(){
        var s=tdyn.value.trim();
        if(!s){ delete w.Dynamic; tdyn.style.borderColor=''; return; }
        try{ w.Dynamic=JSON.parse(s); tdyn.style.borderColor=''; }
        catch(e){ tdyn.style.borderColor='#f85149'; }
      });
      c.appendChild(el('details',{},[el('summary',{text:'高级：Dynamic（原始 JSON）'}), tdyn]));
      wbox.appendChild(c);
    });
  }
  renderWaves();
  wraps.push(el('div',{},[
    el('button',{text:'＋ 添加波次',onclick:function(){
      d.Wave.push({Spawn:[{Zombie:(zopts[0]||{}).value,Line:-1,Num:1}],
                   Event:[],DynamicPlantfood:[0,0,0,0,0,0,0]}); renderWaves(); }}),
    wbox
  ]));
  return wraps;
}

/* ---------- 各区块渲染 ---------- */
function dataRawFallback(f){
  /* 整段 Data 原始 JSON 兜底：覆盖 schema 之外的字段，保证往返无损可编辑 */
  var det = el('details',{});
  var ta = el('textarea',{style:'min-height:90px'});
  ta.value = JSON.stringify(f.Data||{},null,1);
  ta.addEventListener('change', function(){
    try{
      var v = JSON.parse(ta.value||'{}');
      if(v && typeof v==='object' && !Array.isArray(v)){ f.Data=v; renderAll(); }
      else ta.style.borderColor='#f85149';
    }catch(e){ ta.style.borderColor='#f85149'; }
  });
  det.appendChild(el('summary',{text:'高级：整段 Data 原始 JSON（含 schema 外字段）'}));
  det.appendChild(ta);
  return det;
}

function featureManager(){
  var box = el('div',{});
  function render(){
    box.innerHTML = '';
    var list = el('div',{});
    (LV.Feature||[]).forEach(function(f, i){
      var known = DATA.featureNames.indexOf(f.Name)>=0;
      var line = el('div',{style:'display:flex;gap:6px;align-items:center;margin:3px 0'},[
        el('span',{class:'chip'},[el('span',{text:(i+1)+'. '+((DATA.featureLabels||{})[f.Name]||f.Name)+' '+f.Name+(known?'':'（未知段，原始JSON）')})]),
        el('span',{class:'sp',style:'flex:1'}),
        el('button',{text:'↑',title:'上移',onclick:function(){
          if(i>0){ var t=LV.Feature[i-1]; LV.Feature[i-1]=f; LV.Feature[i]=t; renderAll(); } }}),
        el('button',{text:'↓',title:'下移',onclick:function(){
          if(i<LV.Feature.length-1){ var t=LV.Feature[i+1]; LV.Feature[i+1]=f; LV.Feature[i]=t; renderAll(); } }}),
        el('button',{class:'danger',text:'删除',onclick:function(){
          if(!confirm('删除 Feature「'+f.Name+'」？')) return;
          LV.Feature.splice(i,1); renderAll(); }})
      ]);
      list.appendChild(line);
    });
    if(!(LV.Feature||[]).length) list.appendChild(el('div',{class:'hint',text:'当前没有任何 Feature 段。'}));
    box.appendChild(list);
    var addSel = el('select',{style:'width:auto;max-width:340px'});
    addSel.appendChild(el('option',{value:'',text:'＋ 添加 Feature…'}));
    DATA.featureNames.forEach(function(n){
      if(feat(n)) return;
      addSel.appendChild(el('option',{value:n,text:((DATA.featureLabels||{})[n]||n)+' ('+n+')'}));
    });
    addSel.addEventListener('change', function(){
      if(!addSel.value) return;
      LV.Feature.push({Name:addSel.value, Data:{}});
      renderAll();
    });
    box.appendChild(row('添加 Feature', addSel,
      '游戏注册的全部 27 种 Feature；依赖（如 Glove 需要 Map+PacketPick）游戏会自动补建，但仍建议按 Map→PacketPick→其它 排序'));
  }
  render();
  return box;
}

/* GemMatch 字段（gmFields 驱动），复用原有逻辑 */
function gemMatchEditor(gd){
  var gkids = [];
  DATA.gmFields.forEach(function(f){
    var has = Object.prototype.hasOwnProperty.call(gd, f.name);
    if(f.name === 'plantList'){
      gd.plantList = gd.plantList || [];
      gkids.push(row(f.label+' ('+f.name+')',
        multiPicker(function(){return gd.plantList;}, function(v){gd.plantList=v;}, DATA.plant)));
    } else if(f.name === 'plantUpgradeList'){
      gd.plantUpgradeList = gd.plantUpgradeList || [];
      gkids.push(row(f.label+' ('+f.name+')', upgradeEditor(gd)));
    } else if(f.type === 'string'){
      gkids.push(row(f.label+' ('+f.name+')',
        selInput(function(){return gd[f.name];}, function(v){
          if(v) gd[f.name]=v; else delete gd[f.name]; }, DATA.plant, true),
        '默认 '+f.default));
    } else if(f.type === 'array'){
      gkids.push(row(f.label+' ('+f.name+')',
        multiPicker(function(){return gd[f.name]||[];}, function(v){gd[f.name]=v;}, DATA.plant)));
    } else {
      var inp = el('input',{type:'number',step:'any',value:(has?gd[f.name]:'')});
      inp.addEventListener('input', function(){
        if(inp.value==='') delete gd[f.name]; else gd[f.name]=Number(inp.value);
      });
      gkids.push(row(f.label+' ('+f.name+')', inp,
        (f.derived?'派生字段，留空则由游戏取关联字段的值；':'')+'留空=不写入，游戏默认 '+f.default));
    }
  });
  return gkids;
}

/* 单个 Feature 的编辑卡片 */
function featureSection(f, idx){
  var n = f.Name;
  var zh = (DATA.featureLabels||{})[n] || n;
  if(!f.Data || typeof f.Data!=='object' || Array.isArray(f.Data)) f.Data = {};
  var depTips = {
    Glove: 'Glove 无任何配置字段（Data={}）。依赖 Map+PacketPick（游戏自动补建）。',
    Camera: 'Camera 无配置字段（官方 Data 为 {}），参数由地图配置决定。',
    Hammer: 'Hammer 无配置字段（Data={}）。',
    Shovel: 'Shovel 的 Data 游戏不读取（Init() 忽略 data）。要让关卡真正发放铲子，请用上方「奖励 Reward」把收藏品设为铲子；下方 ShovelName 仅作 JSON 备忘。',
    WarningLine: 'WarningLine 无关卡级配置（Data={}）。',
    LookStar: 'LookStar 无常规关卡配置，具体字段用下方原始 JSON 编辑。',
    Portal: 'Portal 的 portals 数组结构较复杂，用下方原始 JSON 编辑。',
    PacketPick: 'PacketPick 通常留空 {}（全部走默认值）。'
  };
  if(n === 'Wave'){
    return section('Feature · '+zh+' Wave（'+(idx+1)+'）','波次与出怪',
      waveEditor().concat([dataRawFallback(f)]));
  }
  if(n === 'GemMatch'){
    var gd = fd('GemMatch');
    var kids = gemMatchEditor(gd);
    kids.push(el('div',{class:'hint',
      text:'植物属性覆盖 plantOverride 为构建器扩展段，游戏当前不读取——棋盘植物由游戏用全局卡牌配置创建；导出时仍会写入。'}));
    kids.push(plantOverrideEditor());
    kids.push(dataRawFallback(f));
    return section('Feature · '+zh+' GemMatch（'+(idx+1)+'）','宝石迷阵核心参数', kids);
  }
  var sch = SCHEMAS[n];
  if(sch === undefined){
    /* 未知 Feature：原始 JSON 兜底，往返无损 */
    return section('Feature · '+n+'（'+(idx+1)+'）','未知段 · 原始 JSON', [
      el('div',{class:'hint',text:'该 Feature 不在已知清单中，Data 用原始 JSON 编辑，导出时原样保留。'}),
      dataRawFallback(f)
    ]);
  }
  var kids = [];
  if(depTips[n]) kids.push(el('div',{class:'hint',text:depTips[n]}));
  if(!sch.length && !depTips[n]) kids.push(el('div',{class:'hint',text:'该 Feature 无常规配置字段（Data={}）。'}));
  sch.forEach(function(sf){ kids.push(schemaField(f.Data, sf, renderAll)); });
  if(n === 'NpcTalk') kids.push(talkEditor(f.Data));
  if(n === 'Tutorial') kids.push(tutorialEditor(f.Data));
  kids.push(dataRawFallback(f));
  return section('Feature · '+zh+' '+n+'（'+(idx+1)+'）', '', kids);
}

/* Process（游戏模式）编辑器 */
function processEditor(){
  var box = el('div',{});
  /* 纯扁平关卡可能原本没有 Process 段：不自动创建，保住往返无损 */
  if(!LV.Process || typeof LV.Process!=='object' || Array.isArray(LV.Process)){
    box.appendChild(el('div',{class:'hint',
      text:'当前关卡没有 Process 段（游戏按旧扁平格式解析）。如需指定游戏模式，请手动添加。'}));
    box.appendChild(el('button',{text:'＋ 添加 Process 段',onclick:function(){
      LV.Process = {Name:'Wave', Data:{}};
      RAWFLAGS.process = true;
      renderAll();
    }}));
    return box;
  }
  var p = LV.Process;
  if(p.Data===undefined || p.Data===null ||
     typeof p.Data!=='object' || Array.isArray(p.Data)) p.Data = {};
  box.appendChild(row('Process.Name（游戏模式）',
    selInput(function(){return p.Name;}, function(v){
      if(v === p.Name) return;
      if(!confirm('切换游戏模式将把 Process.Data 重置为空对象，确定？')) { renderAll(); return; }
      p.Name = v; p.Data = {}; renderAll();
    }, DATA.processNames.map(function(n){
      var zh = (DATA.processLabels||{})[n];
      return {label:(zh? zh+' · '+n : n), value:n};
    }), false),
    PTIPS[p.Name] || null));
  var sch = PSHEMAS[p.Name] || [];
  if(!sch.length) box.appendChild(el('div',{class:'hint',text:'该模式 Data 为空对象 {}。'}));
  sch.forEach(function(f){ box.appendChild(schemaField(p.Data, f, renderAll)); });
  var det = el('details',{});
  var ta = el('textarea',{style:'min-height:70px'});
  ta.value = JSON.stringify(p.Data||{},null,1);
  ta.addEventListener('change', function(){
    try{
      var v = JSON.parse(ta.value||'{}');
      if(v && typeof v==='object' && !Array.isArray(v)){ p.Data=v; renderAll(); }
      else ta.style.borderColor='#f85149';
    }catch(e){ ta.style.borderColor='#f85149'; }
  });
  det.appendChild(el('summary',{text:'高级：Process.Data 原始 JSON'}));
  det.appendChild(ta);
  box.appendChild(det);
  return box;
}

function renderAll(){
  var app = document.getElementById('app');
  app.innerHTML = '';
  if(!Array.isArray(LV.Feature)) LV.Feature = [];

  /* 元信息 */
  var m = [];
  ['Name','Description','LevelName','NextLevel','HomeWorld'].forEach(function(k){
    m.push(row(k, txtInput(function(){return LV[k];}, function(v){LV[k]=v;})));
  });
  ['LevelNumber','Version'].forEach(function(k){
    m.push(row(k, numInput(function(){return LV[k];}, function(v){LV[k]=v;}, 'any')));
  });
  app.appendChild(section('关卡元信息','LevelName 可用 {LevelNumber}', m));

  /* 奖励（游戏唯一「关卡发铲子」的生效路径） */
  app.appendChild(section('奖励 Reward','通关奖励：卡牌 / 收藏品(含铲子) / 金币 / 奖杯', [rewardEditor()]));

  /* Feature 管理 */
  app.appendChild(section('Feature 管理','共 '+LV.Feature.length+' 段，可增删排序', [featureManager()]));

  /* 各 Feature 编辑卡片（按 LV.Feature 顺序渲染） */
  LV.Feature.forEach(function(f, i){ app.appendChild(featureSection(f, i)); });

  /* Process（游戏模式） */
  app.appendChild(section('Process · 游戏模式','决定通关方式 FinishMethod', [processEditor()]));

  document.getElementById('stat').textContent =
    '植物 '+DATA.meta.plant+' · 僵尸 '+(DATA.meta.zombie+DATA.meta.zombieExtra)+
    ' · 属性 '+DATA.meta.property+' · Feature '+LV.Feature.length+' 段 · 波次 '+((fd('Wave')||{}).Wave||[]).length;
}

/* ---------- 奖励 Reward 编辑器 ---------- */
/* 对应 TowerDefenseLevelConfig.Export(): Reward{RewardType, RewardFirst}
   RewardType ∈ {NOONE, PACKET, COLLECTABLE, COIN, TROPHY}（LEVEL_REWARDTYPE）
   COLLECTABLE 时会 SetFeatureValue(key,true) 解锁；若为铲子收藏品，游戏还会把它设为 CurrentShovel */
function rewardEditor(){
  var REWARD_TYPES = [
    {label:'无奖励 Noone', value:'Noone'},
    {label:'卡牌奖励 Packet', value:'Packet'},
    {label:'收藏品奖励 Collectable（含铲子）', value:'Collectable'},
    {label:'金币奖励 Coin', value:'Coin'},
    {label:'奖杯奖励 Trophy', value:'Trophy'},
  ];
  var box = el('div',{});
  function render(){
    box.innerHTML='';
    LV.Reward = LV.Reward || {};
    var r = LV.Reward;
    var curType = val(r.RewardType,'Noone');

    /* 类型下拉 */
    box.appendChild(row('奖励类型 RewardType',
      selInput(function(){return r.RewardType;},
        function(v){ if(v==='') delete r.RewardType; else r.RewardType=v; render(); },
        REWARD_TYPES, false)));

    /* 值 */
    if(curType === 'Collectable'){
      box.appendChild(row('收藏品 RewardFirst',
        selInput(function(){return r.RewardFirst;},
          function(v){ if(v==='') delete r.RewardFirst; else r.RewardFirst=v; },
          DATA.collectable, true),
        '铲子类收藏品解锁后，游戏会自动把它设为当前铲子（CurrentShovel）'));
      box.appendChild(el('div',{class:'hint',
        text:'💡 想让关卡「发一把铲子」：这里选对应铲子收藏品即可（游戏 TowerDefenseAwardCollectable 会把 CurrentShovel 切成它）。'}));
    } else if(curType === 'Packet'){
      box.appendChild(row('卡牌 RewardFirst',
        selInput(function(){return r.RewardFirst;},
          function(v){ if(v==='') delete r.RewardFirst; else r.RewardFirst=v; },
          DATA.plant, true),
        '解锁该卡牌（RewardFirst 也支持数组，多张卡用下方原始 JSON 编辑）'));
    } else if(curType === 'Coin'){
      box.appendChild(row('金币数量 RewardFirst',
        numInput(function(){return r.RewardFirst;},
          function(v){ if(v===null) delete r.RewardFirst; else r.RewardFirst=v; }, 1),
        '游戏默认 2000'));
    } else if(curType === 'Trophy'){
      box.appendChild(el('div',{class:'hint',text:'奖杯奖励无需额外参数（游戏固定使用奖杯结算流程）。'}));
    } else {
      box.appendChild(el('div',{class:'hint',text:'无奖励 / 未设置：游戏将走默认奖励流程。'}));
    }
  }
  render();
  return box;
}

function upgradeEditor(gd){
  var box = el('div',{});
  function render(){
    box.innerHTML = '';
    var tb = el('table',{},[el('thead',{},[el('tr',{},[
      el('th',{text:'来源植物 from'}), el('th',{text:'升级为 to'}), el('th',{text:'消耗 cost'}), el('th',{text:''})
    ])])]);
    var tbody = el('tbody',{});
    (gd.plantUpgradeList||[]).forEach(function(u,i){
      tbody.appendChild(el('tr',{},[
        el('td',{},[selInput(function(){return u.from;}, function(v){u.from=v;}, DATA.plant, false)]),
        el('td',{},[selInput(function(){return u.to;}, function(v){u.to=v;}, DATA.plant, false)]),
        el('td',{},[el('input',{type:'number',step:'any',value:val(u.cost,0),
          oninput:function(e){ u.cost=Number(e.target.value); }})]),
        el('td',{},[el('button',{class:'danger',text:'删除',onclick:function(){
          gd.plantUpgradeList.splice(i,1); render(); }})])
      ]));
    });
    tb.appendChild(tbody);
    box.appendChild(tb);
    box.appendChild(el('button',{text:'＋ 添加升级链',onclick:function(){
      gd.plantUpgradeList = gd.plantUpgradeList || [];
      gd.plantUpgradeList.push({from:(DATA.plant[0]||{}).value, to:(DATA.plant[1]||{}).value, cost:1000});
      render(); }}));
    // 清空后不残留空数组（保持与官方"只写非默认字段"一致）
    if(gd.plantUpgradeList && !gd.plantUpgradeList.length) delete gd.plantUpgradeList;
  }
  render();
  return box;
}

/* ---------- 植物属性覆盖（自定义扩展段 Feature[GemMatch].Data.plantOverride） ----------
   结构 { 植物ID: TowerDefenseCharacterOverride }，与僵尸覆盖完全一致，复用同一个
   overrideEditor 组件。注意：游戏当前不读取此段（棋盘植物由游戏用全局卡牌配置创建）。 */
function plantOverrideEditor(){
  var box = el('div',{});
  function poGet(){ var gd = ensureFeat('GemMatch'); return gd.plantOverride || null; }
  function poEnsure(){ var gd = ensureFeat('GemMatch');
    if(!gd.plantOverride) gd.plantOverride = {}; return gd.plantOverride; }
  function render(){
    box.innerHTML = '';
    var po = poGet() || {};
    var ids = Object.keys(po);
    if(!ids.length) box.appendChild(el('div',{class:'hint',text:'尚未配置任何植物覆盖。'}));
    ids.forEach(function(id){
      var m = DATA.plant.filter(function(p){ return p.value===id; })[0];
      var card = el('div',{class:'card'},[
        el('div',{class:'hd'},[
          el('span',{class:'ttl',text:(m? m.label+' ('+id+')' : id)}),
          el('span',{class:'sp'}),
          el('button',{class:'danger',text:'删除',onclick:function(){
            delete po[id];
            if(!Object.keys(po).length){ var gd = feat('GemMatch'); if(gd) delete gd.Data.plantOverride; }
            render();
          }})
        ])
      ]);
      card.appendChild(overrideEditor(po[id], '植物覆盖', {mode:'plant', lockUid:id}));
      box.appendChild(card);
    });
    var addSel = el('select',{style:'width:auto;max-width:340px'});
    addSel.appendChild(el('option',{value:'',text:'＋ 选择要覆盖的植物…'}));
    DATA.plant.forEach(function(p){
      if(po[p.value]) return;
      addSel.appendChild(el('option',{value:p.value,text:p.label+' ('+p.value+')'}));
    });
    addSel.addEventListener('change', function(){
      if(!addSel.value) return;
      poEnsure()[addSel.value] = {};
      render();
    });
    box.appendChild(addSel);
  }
  render();
  return box;
}

/* 递归清理覆盖对象中的空数组/空对象；返回 null 表示该对象已空可删除。
   注意：null 标量要保留（PropertyChange 条目允许 Value:null）。 */
function pruneOverride(o){
  if(!o || typeof o !== 'object') return null;
  Object.keys(o).forEach(function(k){
    var v = o[k];
    if(Array.isArray(v)){ if(!v.length) delete o[k]; }
    else if(v && typeof v === 'object'){ if(!pruneOverride(v)) delete o[k]; }
  });
  return Object.keys(o).length ? o : null;
}
function pruneAll(){
  /* 只清理覆盖对象「内部」的空数组/空对象；已存在的覆盖键本身保留，
     以保证导入→导出往返无损（官方关卡里 SpawnOverride 常为空 {}）。
     新建关卡因惰性创建，不会凭空多出这些键。 */
  var wd = fd('Wave') || {};
  if(wd.SpawnOverride) pruneOverride(wd.SpawnOverride);
  (wd.Wave || []).forEach(function(w){
    (w.Spawn || []).forEach(function(s){
      if(s.Override) pruneOverride(s.Override);
    });
  });
  var gd = fd('GemMatch') || {};
  if(gd.plantOverride){
    Object.keys(gd.plantOverride).forEach(function(id){
      pruneOverride(gd.plantOverride[id]);
    });
    if(!Object.keys(gd.plantOverride).length) delete gd.plantOverride;
  }
  /* NpcTalk 的 Arg：去掉空槽位；空数组则删键（对应游戏侧 NpcTalkHandConfig 的 Arg[0..3]） */
  var nd = fd('NpcTalk') || {};
  (nd.Talk || []).forEach(function(t){
    if(Array.isArray(t.Arg)){
      t.Arg = t.Arg.map(function(s){ return (typeof s === 'string') ? s.trim() : s; })
                   .filter(function(s){ return s !== '' && s !== undefined && s !== null; });
      if(!t.Arg.length) delete t.Arg;
    }
  });
}

/* ---------- 序列化：tab 缩进，整数写成 X.0（对齐官方风格） ---------- */
function ser(v, ind){
  ind = ind || '';
  var t = typeof v;
  if(v === null || v === undefined) return 'null';
  if(t === 'boolean') return v ? 'true' : 'false';
  if(t === 'number') return Number.isInteger(v) ? v.toFixed(1) : String(v);
  if(t === 'string') return JSON.stringify(v);
  if(Array.isArray(v)){
    if(!v.length) return '[]';
    return '[\n' + v.map(function(x){ return ind+'\t'+ser(x, ind+'\t'); }).join(',\n') + '\n'+ind+']';
  }
  var ks = Object.keys(v);
  if(!ks.length) return '{}';
  return '{\n' + ks.map(function(k){
    return ind+'\t'+JSON.stringify(k)+': '+ser(v[k], ind+'\t'); }).join(',\n') + '\n'+ind+'}';
}

/* ---------- 导出 / 导入 / 校验 ---------- */
function buildOut(){
  pruneAll();
  /* 直接序列化工作对象 LV：未知顶层键（WaveManager/Event/PreSpawn/Progress 等）
     与未知 Feature 段原样保留，实现往返无损。
     仅当原文件本就没有 Feature/Process 且编辑后仍为空时，不写出该键。 */
  var o = JSON.parse(JSON.stringify(LV));
  if(!RAWFLAGS.feature && (!o.Feature || !o.Feature.length)) delete o.Feature;
  if(!RAWFLAGS.process && !o.Process) delete o.Process;
  return o;
}

function validate(){
  var d = buildOut(), fails = [], warns = [];
  function ck(c,m){ if(!c) fails.push(m); }
  ck('Name' in d, '缺少顶层 Name');
  /* Feature 段校验 */
  var names = (d.Feature||[]).map(function(f){return f.Name;});
  names.forEach(function(n,i){
    var f = d.Feature[i];
    if(!('Name' in f) || !('Data' in f)) fails.push('Feature['+i+'] 缺少 Name/Data');
    else if(f.Data===null || typeof f.Data!=='object' || Array.isArray(f.Data))
      fails.push('Feature['+i+'] '+n+' 的 Data 不是对象');
  });
  names.forEach(function(n,i){
    if(names.indexOf(n) !== i) fails.push('Feature 段重名：'+n+'（游戏按名索引，将只有最后一段生效）');
  });
  names.forEach(function(n){
    if(DATA.featureNames.indexOf(n)<0) warns.push('Feature「'+n+'」不在游戏注册清单中，导出后游戏可能忽略');
  });
  /* Process 校验 */
  if('Process' in d){
    var pn = d.Process && d.Process.Name;
    ck(DATA.processNames.indexOf(pn)>=0, 'Process.Name「'+pn+'」不是有效模式（'+DATA.processNames.join('/')+'）');
  } else {
    warns.push('关卡没有 Process 段（纯扁平格式），游戏将按旧格式解析');
  }
  /* Wave 波次结构 */
  var wd = (fd('Wave')||{});
  (wd.Wave||[]).forEach(function(w,i){
    ['Spawn','Event','DynamicPlantfood'].forEach(function(k){
      if(!(k in w)) fails.push('Wave['+i+'] 缺少 '+k);
    });
  });
  /* 奖励合法性 */
  if('Reward' in d){
    var rw = (d.Reward && typeof d.Reward==='object' && !Array.isArray(d.Reward)) ? d.Reward : null;
    if(!rw){
      fails.push('Reward 段必须是对象');
    } else {
      var RT = ['Noone','Packet','Collectable','Coin','Trophy'];
      var rt = rw.RewardType;
      if(rt===undefined || rt===null || rt===''){
        warns.push('Reward.RewardType 未设置，游戏按 NOONE 处理');
      } else {
        ck(RT.indexOf(rt)>=0, 'Reward.RewardType「'+rt+'」不是有效值（'+RT.join('/')+'，大小写敏感）');
      }
      var known = {};
      DATA.collectable.forEach(function(o){ known[o.value]=1; });
      if(rw.RewardType==='Collectable' && typeof rw.RewardFirst==='string' && rw.RewardFirst && !known[rw.RewardFirst]){
        warns.push('Reward.RewardFirst「'+rw.RewardFirst+'」不在收藏品清单中，游戏可能解锁失败');
      }
    }
  }
  /* 铲子提示 */
  var sv = (fd('Shovel')||{});
  if(sv.ShovelName){
    warns.push('Feature·Shovel 的 ShovelName 游戏不读取（仅写入 JSON 备忘）；发放铲子请走 Reward=Collectable');
  }
  /* GemMatch 字段合法性 */
  var gm = (fd('GemMatch')||{});
  var legal = {}; DATA.gmFields.forEach(function(f){ legal[f.name]=1; });
  legal['plantOverride'] = 1;   // 构建器扩展段，允许存在
  Object.keys(gm).forEach(function(k){ if(!legal[k]) fails.push('GemMatch 含非法字段 '+k); });
  if(gm.plantOverride && Object.keys(gm.plantOverride).length){
    warns.push('plantOverride 为构建器扩展段，游戏当前不读取（棋盘植物走全局卡牌配置）');
  }
  /* 依赖提示（游戏会自动补建依赖，但显式声明更稳） */
  function hasF(n){ return names.indexOf(n)>=0; }
  if((hasF('Glove')||hasF('RainMode')) && !(hasF('Map')&&hasF('PacketPick')))
    warns.push('Glove/RainMode 依赖 Map+PacketPick（游戏会自动补建，建议显式添加）');
  if(hasF('ConveyorBelt') && !hasF('PacketPick'))
    warns.push('ConveyorBelt 依赖 PacketPick（游戏会自动补建，建议显式添加）');
  if(hasF('Wave') && !(hasF('Map')&&hasF('Progress')))
    warns.push('Wave 依赖 Map+Progress（游戏会自动补建，建议显式添加）');
  if(hasF('Wave') && !((wd.Wave||[]).length)) warns.push('Wave 段尚未配置任何波次');
  return {fails:fails, warns:warns, data:d};
}

function showReport(r){
  var old = document.getElementById('rptSec');
  if(old) old.remove();
  var lines = [];
  if(!r.fails.length) lines.push('<span class="ok">✔ 校验全部通过</span>');
  else r.fails.forEach(function(m){ lines.push('<span class="bad">✘ '+m+'</span>'); });
  r.warns.forEach(function(m){ lines.push('<span class="wn">! '+m+'</span>'); });
  var sec = el('section',{},[el('h2',{},[el('span',{text:'校验结果'})]),
    el('div',{class:'body'},[el('div',{id:'report'})])]);
  sec.querySelector('#report').innerHTML = lines.join('\n');
  document.getElementById('app').appendChild(sec);
  sec.scrollIntoView({behavior:'smooth'});
}

function download(text, name){
  var blob = new Blob([text], {type:'application/json;charset=utf-8'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(function(){ URL.revokeObjectURL(a.href); }, 1000);
}
/* 导出：优先调用系统「另存为」对话框（可自选文件夹与文件名）；
   浏览器不支持（如旧内核 / 非安全上下文）时回退为普通下载 */
function saveText(text, name){
  if(!window.showSaveFilePicker){ download(text, name); return; }
  try{
    window.showSaveFilePicker({
      suggestedName: name,
      types: [{description:'JSON 关卡文件', accept:{'application/json':['.json']}}]
    }).then(function(handle){
      return handle.createWritable().then(function(w){
        return Promise.resolve(w.write(new Blob([text],{type:'application/json;charset=utf-8'})))
          .then(function(){ return w.close(); });
      });
    }).catch(function(e){
      if(e && e.name === 'AbortError') return;   // 用户取消，静默
      download(text, name);                      // 其它异常 → 回退下载
    });
  }catch(e){
    download(text, name);
  }
}

/* ---------- 事件绑定 ---------- */
document.getElementById('btnNew').onclick = function(){
  if(!confirm('新建将丢弃当前编辑内容，确定？')) return;
  LV = JSON.parse(JSON.stringify(DATA.template));
  RAWFLAGS = {feature: true, process: true};
  renderAll();
};
document.getElementById('btnValidate').onclick = function(){ showReport(validate()); };
document.getElementById('btnExport').onclick = function(){
  var r = validate();
  var out = ser(r.data) + '\n';
  var nm = (LV.Name || 'level') + '.json';
  if(r.fails.length){
    showReport(r);
    if(!confirm('存在 '+r.fails.length+' 项校验错误，仍要导出吗？')) return;
  }
  saveText(out, nm);
};
document.getElementById('fileInput').onchange = function(e){
  var f = e.target.files[0];
  if(!f) return;
  var fr = new FileReader();
  fr.onload = function(){
    try{
      var o = JSON.parse(fr.result);
      if(!o || typeof o!=='object' || Array.isArray(o)){ alert('这不是关卡 JSON 对象'); return; }
      LV = o;
      /* 往返无损：记录原文件的顶层键情况；纯扁平格式（无 Feature）也能编辑 */
      RAWFLAGS = {feature: Array.isArray(o.Feature), process: ('Process' in o)};
      if(!RAWFLAGS.feature) LV.Feature = [];
      if(LV.Process && (typeof LV.Process!=='object' || Array.isArray(LV.Process))) LV.Process = {Name:'Wave', Data:{}};
      renderAll();
      showReport(validate());
    }catch(err){ alert('JSON 解析失败：'+err.message); }
  };
  fr.readAsText(f, 'utf-8');
  e.target.value = '';
};

/* ---------- 启动 ---------- */
LV = JSON.parse(JSON.stringify(DATA.template));
RAWFLAGS = {feature: true, process: true};
/* 调试/自动化验收钩子：暴露工作对象与导出/校验函数（只读使用不影响 UI） */
window.__builder_dbg = {
  getLV: function(){ return JSON.parse(JSON.stringify(LV)); },
  setLV: function(o){
    LV = JSON.parse(JSON.stringify(o));
    RAWFLAGS = {feature: Array.isArray(o.Feature) || Array.isArray(LV.Feature),
                process: ('Process' in o) || !!LV.Process};
    if(!Array.isArray(LV.Feature)) LV.Feature = [];
    renderAll();
  },
  buildOut: buildOut,
  validate: validate,
  version: 'fullmode'
};
try { renderAll(); }
catch(e){ document.getElementById('stat').textContent = '初始化失败: ' + (e && e.stack || e); }
})();
</script>
</body>
</html>
'''

def main():
    payload = json.dumps(DATA, ensure_ascii=False, separators=(",", ":"))
    # 防止 JSON 中的 </script 提前闭合脚本块（JSON 合法转义 \/ ）
    payload = payload.replace("</", "<\\/")
    html = HTML.replace("__DATA__", payload)
    out = os.path.join(BASE, "gemmatch_builder.html")
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print("generated ->", out)
    print("html size : %.1f KB" % (os.path.getsize(out) / 1024.0))
    print("data      : plant=%d zombie=%d+%d item=%d armor=%d property=%d attribute=%d event=%d gmFields=%d" % (
        DATA["meta"]["plant"], DATA["meta"]["zombie"], DATA["meta"]["zombieExtra"],
        DATA["meta"]["item"], DATA["meta"]["armor"],
        DATA["meta"]["property"], DATA["meta"]["attribute"],
        DATA["meta"]["event"], len(DATA["gmFields"])))
    print("presets   : packetBankType=%d categoryName=%d mowerItems=%d talkAudio=%d talkAnime=%d talkArgPresets=%d shovels=%d" % (
        len(DATA["packetBankType"]), len(DATA["categoryName"]), len(DATA["mowerItems"]),
        len(DATA["talkAudio"]), len(DATA["talkAnime"]), len(DATA["talkArgPresets"]), len(DATA["shovels"])))
    print("feature   :", "/".join(DATA["featureOrder"]))


if __name__ == "__main__":
    main()
