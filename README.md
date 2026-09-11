# 杂交版关卡构建器 · 说明文档

> 《植物大战僵尸杂交版》关卡构建器改造项目 —— 功能总览 & 相对官方构建器的改进
>
> 最后更新：2026-09-11

---

## 0. 这是什么

本项目围绕**官方关卡构建器 v0.27**（`pvzhe-level-builder.exe`）做1件事：

| 线路 | 载体 | 做法 |
|---|---|---|
| **B. 全模式构建器**（自制） | `gemmatch_builder.html`（由 `build_gemmatch_builder.py` 生成） | 单文件 HTML，浏览器直接打开；补齐官方 exe **架构上做不到**的能力 |

**B线工作**：B 用于编辑官方 exe **无法编辑**的 Feature/Process 新格式关卡，并提供更强的预设、覆盖编辑器与往返无损保证。

---

## 1. 快速开始

### B. 全模式构建器（推荐，功能更全）

1. 浏览器（新版 Chromium 内核）打开 `gemmatch_builder.html` —— 单文件、零依赖、无需服务器
2. 顶部 **导入** 载入已有 `.json` 关卡，或 **新建** 从模板开始
3. 左侧按 Feature 分段编辑，底部 **校验** / **导出**
4. 导出优先弹出系统「另存为」对话框（可自选文件夹与文件名），不支持时自动回退为普通下载

> **开发者注意**：`gemmatch_builder.html` 是**生成产物**，请勿手改。
> 要改功能 → 改 `build_gemmatch_builder.py` → 重跑 `python build_gemmatch_builder.py`。

### C. 命令行生成（GemMatch 专用）

```bash
python gen_gemmatch_level.py            # 交互模式
python gen_gemmatch_level.py --template # 模板模式
python gen_gemmatch_level.py --validate # 校验模式
```

---

## 2. 全模式构建器的功能

### 2.1 全模式覆盖：27 个 Feature + 6 个 Process

官方构建器只能编辑「扁平 24 字段」的老格式关卡；**新格式关卡**（`Feature:[{Name,Data}×N] + Process`）在
官方 exe 内属于硬编码子表单，纯配置无法触达。全模式构建器把这一层完全打开：

**Feature（27 种，全部可增删排序）**

| 类别 | Feature |
|---|---|
| 核心 | `Wave` `Map` `BGM` `Camera` `Progress` `PacketPick` `SeedBank` `Sun` |
| 卡牌/工具 | `PacketBank` `Mower` `Brain` `Shovel` `Glove` `Hammer` `SlotMachine` |
| 玩法机制 | `RainMode` `ConveyorBelt` `Fog` `ScreenEffect` `Portal` `LookStar` `WarningLine` |
| 演出/教学 | `NpcTalk` `Tutorial` `Event` `PreSpawn` |
| 小游戏 | `GemMatch` |

**Process（6 种游戏模式）**：`Wave`（常规波次）/ `Vase`（花瓶）/ `IZM`（我是僵尸）/ `IZM2` / `Quiz`（答题）/ `Empty`
—— 切换即决定 `FinishMethod`，各模式有专属字段表单。

### 2.2 往返无损（Round-trip Safe）

这是全模式构建器最关键的工程性质：

- **未知顶层键原样保留**：`WaveManager` / `Event` / `PreSpawn` / `Progress` / `Reward` / `VaseManager` 等扁平段，导入再导出**逐键一致**
- **未知 Feature 段原样保留**：含官方独有、构建器未登记的段，走「整段 Data 原始 JSON」兜底
- **不凭空造键**：原文件没有的 `Feature`/`Process` 键，编辑后仍为空时不写出（`RAWFLAGS` 标记）
- **空值不写入**：所有编辑器遵循「空则删键」，避免导出 `"X":[]` / `"X":{}` 噪声
- **纯扁平关卡也能编辑**：导入不强制要求 Feature+Process 双全

> 已实测：将官方 `template.json`（15 段 Feature）导入→导出，**逐键比对全部一致**。

### 2.3 属性覆盖编辑器（PropertyChange）

- **两种加入方式**
  - **单选即出框**：下拉选一个属性 → 立刻在下方生成带「值」输入框的编辑卡片
  - **勾选批量加入**：搜索 + 勾选多个 → 一次性加入
  - 另有 **＋自定义属性**（不在预设里的属性名可直接输，类型可选 数字/文本/布尔/JSON）
- **按单位过滤**：选择单位后按 `whitelist` 过滤可用属性
- **类型感知取值控件**：枚举下拉 / 多选池 / 数字 / 布尔 / 字符串 / 原始 JSON 自动匹配
- **嵌套覆盖全宽展开**：属性覆盖内再套属性覆盖时，**在下方整行展开**（官方同款观感），不会挤在右侧变窄

### 2.4 卡牌覆盖（`TowerDefensePacketOverride`）可视化编辑

在 死亡/生成事件、RainMode / ConveyorBelt 的掉落包、传送带增卡 等位置提供结构化编辑：

品质 `类型` / 基础价格 `Cost` / 后续种植涨价 `CostRise`·`CostMultiple` / 卡牌冷却 `PacketCooldown`·
`StartingCooldown` / 权重 `Weight` / 波次点数 `WavePointCost` / 种植覆盖 `PlantCover` /
格数限制 `IslimitGridNum` / 直接种植 `CoverCanDirectPlant` / 魅惑 `Hypnoses` / **角色覆盖 `CharacterOverride`**

### 2.5 中文预设体系

所有下拉/预设均显示中文，覆盖：

| 预设 | 内容 |
|---|---|
| 植物 / 僵尸 / 僵尸Extra / 道具 | 324 / 167 / 105 / 56 项，均带中文名 |
| 地图 | 43 项（含尺寸提示） |
| BGM | 12 项（背景音乐 + 兼容键） |
| 卡池 | 22 个（`packetBankAll` / `packetBankType`） |
| 品质 / 卡牌类型 | 11 / 11 项 |
| 装甲 | 44 项（可按单位过滤） |
| **染色预设** | 33 项 `#RRGGBBAA`（含纯白/灰白及其 50%·75% 半透明变体） |
| **铲子** | 11 把（铁铲/金铲/寒冰铲/钻石铲/辣椒铲/磁力铲/西瓜铲/南瓜铲/海盗铲/骷髅铲/爆能铲） |
| **NpcTalk Arg** | 371 项（植物∪僵尸∪僵尸Extra∪道具去重 + 特殊项） |
| 对话 / 动画 / 音频 | 戴夫 NPC、4 种动画、5 种语音 |
| 枚举中文化 | 阳光移动方式、进度模式与 5 种可见性、供卡方式、雨模式类型、Process 模式名 |

### 2.6 专题编辑器

| 编辑器 | 能力 |
|---|---|
| **NpcTalk 自定义对话** | 对话列表（模式/NPC/文本/动画/音频）；`Text` **支持换行**；`Arg` 槽位编辑器（预设下拉 + 自由输入 + 批量导入 + 排序） |
| **Tutorial 自定义教程** | 步骤列表、广播文本（**可换行**）、条件嵌套（检查角色数量 / 收集阳光） |
| **Reward 通关奖励** | 5 种奖励类型；选 `Collectable` 时列中文收藏品（含 9 把铲子）—— 这是**关卡发铲子的唯一生效路径** |
| **Wave 波次** | 顶层字段 + 波次列表 + 每波出怪/事件 + 全局与单波出怪覆盖 |
| **SlotMachine 转盘卡池** | 类型+数量+权重行内编辑，未编辑行保持原字符串（往返无损） |
| **ConveyorBelt / RainMode** | 掉落包权重编辑、优先发包列表、每卡可编辑覆盖 |
| **Vase / PreSpawn / VaseFill** | 花瓶、填瓶、预种植列表（含各自覆盖） |
| **GemMatch** | 19 个专属字段 + 升级表 + 植物属性覆盖 |

### 2.7 校验与导出

- **内建校验**：Feature 重名 / Data 结构 / `Process.Name` 合法性 / 波次结构 / GemMatch 字段合法性 / Reward 类型与收藏品存在性 / 依赖提示（如 RainMode→Map+PacketPick）
- **导出**：优先 `showSaveFilePicker` 系统「另存为」（可自选文件夹），带降级回退
- **调试钩子**：`window.__builder_dbg = {getLV, setLV, buildOut, validate, version}`，供自动化验收

---

## 3. 相对官方构建器的改进 ★

### 3.1 架构层面：突破官方 exe 的 6 项永久边界

官方 exe 的 `templates.json` 只有 **6 个顶层键**（`classTypeComputed/reward/order/event/attribute/property`），
**没有定义新顶层配置段或子表单的能力** —— 该能力硬编码在 exe 内。这导致以下 6 项纯配置永远做不到：

| # | 官方 exe 做不到的 | 全模式构建器的解决方案 |
|---|---|---|
| 1 | **`Feature` 顶层配置段** | ✅ 27 种 Feature 全支持，可增删排序 |
| 2 | **`Process` 顶层配置段** | ✅ 6 种游戏模式，切换即改 `FinishMethod` |
| 3 | **`WaveManager.Survival` 子表单** | ✅ 走原始 JSON 编辑，往返无损 |
| 4 | **`Event.EventEntry` UI** | ✅ Event Feature 内 `EventInit/Entry/Ready/Start` 四段可视编辑 |
| 5 | **GemMatch / SlotMachine / Quiz 参数 UI** | ✅ 均有专属编辑器（GemMatch 19 字段 / 转盘卡池 / Quiz 13 字段） |
| 6 | **`FinishMethod` 补 QUIZ/EMPTY** | ✅ 由 Process 模式决定，实际生效 |

> 这 6 项在官方 exe 上是**永久阻塞**（改 exe 需重打包 Tauri 应用，超出工具能力）；
> 全模式构建器用「另起一个自建 HTML 构建器」的方式全部绕过。

### 3.2 UI / 交互改进汇总

| 改进 | 说明 |
|---|---|
| **属性覆盖批量加入** | 官方为**单项选择**；全模式构建器支持**搜索 + 勾选批量**，另有「单选即出框」 |
| **嵌套覆盖下方展开** | 官方观感：属性覆盖套属性覆盖时整行在下方展开，不挤在右侧 |
| **卡牌覆盖可视化** | 品质/价格/涨价/格数/直接种植/角色覆盖全部结构化，不再手写 JSON |
| **中文预设全面覆盖** | 官方 exe 的很多下拉只有英文枚举值 |
| **NpcTalk / Tutorial 可视化编辑** | 官方 exe 这两个段是硬编码，无法编辑 |
| **导出可自选文件夹** | 使用系统「另存为」对话框 |
| **文本支持换行** | 对话文本、教程广播文本 |
| **往返无损导出** | 官方 exe 只支持扁平格式；全模式构建器可处理 Feature/Process 新格式并逐键保留未知段 |
| **内建校验** | 结构/枚举/依赖/奖励多重校验 + 警告分级 |
| **自动化验收钩子** | `__builder_dbg` 供脚本化测试 |

---

## 4. 验证与质量保障

| 层级 | 手段 | 现状 |
|---|---|---|
| **生成确定性** | 重跑 `build_gemmatch_builder.py` 两次比对 md5 | ✅ 一致 |
| **离线验收** | `python verify_gemmatch_builder.py` | ✅ **89 项全绿** |
| **运行时冒烟** | `verify_pc_regression.js`（jsdom，真实执行 HTML） | ✅ **24 项全绿** |
| **config 校验** | 各 `verify_*.py` | ✅ 全绿 |

**回归脚本覆盖的关键路径**：属性覆盖从**空状态**出发的三条添加路径（单选即出框 / 勾选批量 / 自定义）
× 两个事件（生成卡牌 `PacketSpawn` / 创建角色卡牌 `PacketCreate`），并断言导出无空数组噪声、运行期零 JS 错误。

> 运行 jsdom 冒烟需指定 node 与 NODE_PATH：
> ```bash
> NODE_PATH="<workbuddy>/binaries/node/workspace/node_modules" \
>   "<workbuddy>/binaries/node/versions/22.22.2-3/node.exe" verify_pc_regression.js
> ```

---

## 5. 边界与限制

### 5.1 已交付但游戏侧未生效

| 属性 | 原因 |
|---|---|
| `swayAmplitude` | 游戏无对应组件。需新增 `SwayComponent` 并在 `PropertyChange.Execute` 路由 |
| `modulateCycle` | 同上，需新增 `ColorCycleComponent` |
| `z_index`（僵尸） | 僵尸跨格移动时游戏会重算层级；植物（静态）有效。持久层级应改 `topLayer`/`itemLayer` |
| `Shovel.ShovelName` | `TowerDefenseBattleFeatureShovel.Init()` 忽略 Data；**发铲子请走 `Reward=Collectable`** |



