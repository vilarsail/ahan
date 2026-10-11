---
name: check-ahan
description: 校对四部阿含经（《长阿含经》chang、《中阿含经》zhong、《杂阿含经》za、《增一阿含经》zengyi）的译文质量（{book}/split/{N}.md），重点检测「近似未翻译」段落（译文仅做标点/个别词替换、仍是文言句式），同时检查译文缺失、颂偈未译、格式问题、翻译错误。产出逐卷质量报告到 {book}/split/{N}.check.md。当用户输入 /check-ahan <book> <start> <end> 或要求"校对某经第 X-Y 卷"、"检查译文质量"时触发。
---

# 角色与目标

你是四部阿含经译文校对 Agent。任务是校对 `{book}/split/` 目录下各卷 `split/{N}.md` 的译文质量，产出报告到 `{book}/split/{N}.check.md`。`{book}` ∈ `chang`（长阿含经，22卷）/ `zhong`（中阿含经，60卷）/ `za`（杂阿含经，50卷）/ `zengyi`（增一阿含经，51卷）。

**核心关注点**：检测「近似未翻译」——译文仅对原文做标点替换、个别字词替换、语序微调，整体仍是文言句式，没有真正转换为现代白话。这是批量翻译最常见的退化现象，必须检出。

# 项目目录结构（重要）

本项目是四部阿含经，各自独立子目录，内部结构一致：

```
chang/                      长阿含经（22 卷，后秦 佛陀耶舍/竺佛念 译）
zhong/                      中阿含经（60 卷，东晋 僧伽提婆 译）
za/                         杂阿含经（50 卷，刘宋 求那跋陀罗 译）
zengyi/                     增一阿含经（51 卷，东晋 僧伽提婆 译）
    每个子目录：
    ├── origin/origin.txt   原始完整经文（大正藏底本，只读参考）
    ├── split/              工作目录
    │   ├── 0.md            整理者前言（不参与任何流水线）
    │   ├── {N}.md          第 N 卷正文：原文段与 *译文* 段交替（N ≥ 1）
    │   ├── {N}.txt         第 N 卷原始原文（无译文，只读参考）
    │   ├── {N}.check.md    校对报告（本 skill 产出）
    │   └── 临时文件（pairs_/check_/issues_ 前缀 JSON）
    ├── {经名}.epub/.pdf    成书
    └── cover.jpg
```

**正文格式（四部经统一）**：空行分块；标题行以 `#` 开头；译文行以 `*` 开头（单行 `*...*`）；其余为原文段。原文段与译文段交替出现。段落号 = 文件内原文段的顺序号（标题不计入）。多行颂偈算一个原文段，其译文也合并为一行。

# 架构设计

```
prepare_check.py  →  {book}/split/pairs_{N}.json + check_{N}_batch*.json
    →  [LLM 逐段校对]  →  {book}/split/issues_{N}_batch*.json
    →  build_report.py  →  {book}/split/{N}.check.md
```

- `prepare_check.py`：机械提取「原文段→译文段」对，按批切块（含前 2 段上下文）。**不做任何质量判断**。
- LLM：读取每批的**全量原文+译文**，逐段判断质量问题，写 issues JSON。**判断全部由 LLM 完成**——因为校对需要看全量信息才能判断"近似未翻译"这种语义性问题。
- `build_report.py`：合并各批 issues → 生成 `{book}/split/{N}.check.md`。

# 段落定义

- 段落对 = `split/{N}.md` 中「一个原文段（非 `#`、非 `*` 开头的连续文本块，可多行颂偈）」+「紧跟其后的 `*` 开头译文段（单行）」
- 段落号与 `prepare_check.py` / `fix-ahan` / `smooth-ahan` 同一序号体系（原文段顺序号，标题不计入）
- 标题行（`#`/`##`）不算段落，不校对
- 空行仅作分隔

# 校对维度

逐段检查，命中任一即记录问题（详细判别标准见 AGENT_INSTRUCTIONS.md）：

| 代号 | 类型 | 说明 |
|------|------|------|
| MISSING | 译文缺失 | 原文段后无译文 |
| NEAR-COPY | 近似未翻译 ★重点 | 译文仅做标点/个别词替换，仍是文言句式，未真正白话化 |
| VERSE-NOT-TRANSLATED | 颂偈未译 | 颂偈照抄原文，未译为通顺白话 |
| FORMAT | 格式问题 | 译文未以 `*` 包裹、含"译文"前缀、标题被翻译 |
| ERROR | 翻译错误 | 误译、漏译、术语错误（人名地名/核心名词被错误意译） |
| OTHER | 其它质量 | 语句不通、失真、前后矛盾 |

**绝不硬凑问题**：段落合格就**不记录**。宁缺毋滥。

# 自动化执行工作流

## 步骤一：准备（确定性脚本）

对每个目标卷 `N`：
```
python3 .claude/skills/check-ahan/prepare_check.py <book> <N>
```
也支持区间：`prepare_check.py <book> <s> <e>`。生成 `{book}/split/pairs_{N}.json` 和 `check_{N}_batch*.json`（每批最多 20 个段对，含前 2 段上下文）。

**批次大小**：20 段/批。校对需逐段对比原文与译文，认知负荷高于生成任务，避免单 Agent 上下文过长导致后半段草率判断。

## 步骤二：并行派发校对子 Agent

**关键**：所有批次必须在同一轮消息中并行派发，确保每个子 Agent 独立校对，互不干扰。对每批派发一个子 Agent（`subagent_type: general-purpose`），prompt 精简（指令在 AGENT_INSTRUCTIONS.md，子 Agent Read 一次命中缓存）：

```
读取 .claude/skills/check-ahan/AGENT_INSTRUCTIONS.md 获取校对指令，按其要求校对。

批次文件：{book}/split/check_{N}_batch{batch_num}.json
输出文件：{book}/split/issues_{N}_batch{batch_num}.json
```

## 步骤三：合并问题 + 生成报告

所有子 Agent 完成后，运行：
```
python3 .claude/skills/check-ahan/build_report.py <book> <N>
```
读取 `pairs_{N}.json` 和所有 `issues_{N}_batch*.json`，生成 `{book}/split/{N}.check.md`。

**JSON 容错**：issues 文件是 LLM 生成的 JSON，可能因值内含 ASCII 双引号/换行未转义而解析失败，脚本自动检测并修复；个别批次无法修复时跳过该批并告警，不影响整体报告。若报告缺失某些段号，说明对应批次文件损坏未能修复，需重新派发该校对批次。

报告格式：
```markdown
# 长阿含经卷3（chang/split/3.md）译文校对报告

- 段落总数：X
- 问题段落数：Y（占 Z%）
- 校对时间：<日期>

## 问题列表

### 段落 3 【近似未翻译】
- **原文**：……
- **译文**：……
- **问题**：……
- **修改建议**：……

## 汇总
- 近似未翻译（NEAR-COPY）：n 段
- ……
```

若某卷**完全没有问题**，报告输出「✅ 未发现译文质量问题，本文件无需修改。」

## 步骤四：清理
删除临时文件：`{book}/split/pairs_{N}.json`、`check_{N}_batch*.json`、`issues_{N}_batch*.json`。

# 大文件处理

- 单卷段落数多（za 可达 300+ 段/卷），批次多时（>8）分轮派发（如每轮 8 个），避免一次性并发过多。
- 多卷、多批次之间均可并行派发。

# 交互反馈

- 启动时，简要确认校对的经书与卷范围。
- 派发后保持静默高效。
- 完成后告知每卷的问题统计。
- 结束时输出简明报告：校对卷数、发现的问题段落总数。
