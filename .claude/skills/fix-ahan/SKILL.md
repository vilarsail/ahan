---
name: fix-ahan
description: 根据 {book}/split/{N}.check.md 的校对意见修复 {book}/split/{N}.md 译文（四部阿含经：chang/zhong/za/zengyi）。逐条判断修改意见是否成立，成立则改写译文（含补译缺译段），不成立则不修；产出修复记录到 {book}/split/{N}.fix.md。脚本做解析/定位/应用，LLM 只做判断与改写。当用户输入 /fix-ahan <book> <start> <end> 或要求"修复某经第 X-Y 卷"、"按校对意见修译文"时触发。
---

# 角色与目标

你是四部阿含经译文修复 Agent。任务是根据 `{book}/split/{N}.check.md` 中记录的校对问题，逐条判断修改意见是否成立：成立则改写对应译文段并替换到 `{book}/split/{N}.md`（缺译段落补译插入）；不成立则不修。最终生成 `{book}/split/{N}.fix.md` 修复记录。`{book}` ∈ `chang`（22卷）/ `zhong`（60卷）/ `za`（50卷）/ `zengyi`（51卷）。

**核心原则：有问题才修，没问题不强行修。** LLM 判断每条意见是否成立，存疑即拒绝。

# 项目目录结构

```
{book}/                    chang=长阿含经 / zhong=中阿含经 / za=杂阿含经 / zengyi=增一阿含经
    split/
        0.md               整理者前言（不参与）
        {N}.md             第 N 卷正文（原文段与 *译文* 段交替）——本 skill 的修改对象
        {N}.check.md       校对报告（check-ahan 产出，本 skill 的输入）
        {N}.fix.md         修复记录（本 skill 产出）
        fix_{N}_*.json     临时文件
```

正文格式：空行分块；原文段（非 `#`/`*` 开头）后紧跟单行 `*译文*` 段；段落号 = 原文段顺序号（标题不计入）。与 check-ahan 完全一致的编号体系。

# 架构设计

```
prepare_fix.py  ->  {book}/split/fix_{N}_pairs.json + fix_{N}_batch*.json
    ->  [LLM 逐条判断]  ->  {book}/split/fix_{N}_batch*.verdict.json
    ->  apply_fix.py  ->  {book}/split/{N}.md (更新) + {book}/split/{N}.fix.md
```

- `prepare_fix.py`：从 `split/{N}.check.md` 解析问题列表，从 `split/{N}.md` 提取「原文段->译文段」对，按批切块（每批 10 条）。**不做任何质量判断**。
- LLM：读取每批的**全量原文/译文/问题/建议**，逐条判断修改意见是否成立，成立则改写译文。**判断与改写全部由 LLM 完成**。
- `apply_fix.py`：合并各批判断 -> 应用 ACCEPT 的修复 -> 生成 `split/{N}.fix.md`。

# 判断与改写纪律（详见 AGENT_INSTRUCTIONS.md，此为要点）

## 判断标准（按 type 分别校验）

| 代号 | ACCEPT 条件要点 |
|------|------|
| NEAR-COPY | trans 确实超八成句子原词原句、保留文言虚词/语序（尔时、汝等、云何、所以者何等）；能产出实质白话化的改写 |
| MISSING | trans 确实为空（缺译段，补译） |
| VERSE-NOT-TRANSLATED | 原文为颂偈且 trans 照抄原文；能译为通顺白话 |
| FORMAT | trans 未以 `*` 包裹 / 含"译文"前缀 / 标题被翻译 |
| ERROR | 经核对原文 trans 确实误译/漏译/术语错误，且 suggestion 纠正正确 |
| OTHER | trans 确实不通/失真/矛盾；能产出更好的译文 |

## 改写硬性要求

1. **忠实原文**：不增义、不减义、不歪曲。无把握时保留文言表达，不要凭空意译。
2. **白话化**：除「可保留专有名词」外，文言句式一律改写为白话。
3. **可保留专有名词**：佛/世尊/如来、比丘、比丘尼、阿罗汉、四圣谛、五蕴、十二因缘、八正道、涅槃、帝释、梵天、诸天天名、人名地名（阿难、舍利弗、舍卫国、王舍城、须弥山、阎浮提、由旬、劫等）。**清单外术语一律白话化**（如"苾刍"->"比丘"）。
4. **格式保持**：new_trans 必须是**单行** `*...*`（阿含正文译文一律单行，多行颂偈也译成一行）。
5. **无前缀**：不得添加"译文""翻译""译"等前缀。

## 修复 FORMAT 时只改格式不改译文

FORMAT 问题的 new_trans 与原 trans 文字相同，仅 `*` 包裹调整。

# 自动化执行工作流

## 步骤一：准备（确定性脚本）

对每个目标卷 `N`：
```
python3 .claude/skills/fix-ahan/prepare_fix.py <book> <N>
```
- 解析 `split/{N}.check.md` 提取问题列表
- 从 `split/{N}.md` 提取段落对
- 生成 `split/fix_{N}_pairs.json` 和 `split/fix_{N}_batch*.json`（每批最多 10 条问题，含完整上下文）

**批次大小**：10 条/批。修复判断需逐条对照原文/译文/建议改写，认知负荷高于校对，取 10。

若 `split/{N}.check.md` 显示「本文件无需修改」（无问题段落），跳过该卷。

## 步骤二：并行派发判断子 Agent

**关键**：所有批次必须在同一轮消息中并行派发，确保每个子 Agent 独立判断，互不干扰。对每批派发一个子 Agent（`subagent_type: general-purpose`），prompt 精简：

```
读取 .claude/skills/fix-ahan/AGENT_INSTRUCTIONS.md 获取修复判断指令，按其要求判断并改写。

批次文件：{book}/split/fix_{N}_batch{batch_num}.json
输出文件：{book}/split/fix_{N}_batch{batch_num}.verdict.json
```

**输出与输入分离**：子 Agent 读取批次文件后，将判断结果写入 `.verdict.json`（与输入文件同名但扩展名不同）。原始批次文件保留，便于子 Agent 失败时重试。

## 步骤三：应用修复 + 生成报告

所有子 Agent 完成后，运行：
```
python3 .claude/skills/fix-ahan/apply_fix.py <book> <N>
```
- 合并各批 `.verdict.json` 中的 verdicts
- 对每条 ACCEPT 进行**格式校验**（`*` 包裹、单行）——校验失败的标记为「校验失败」不应用
- 对校验通过的段落：定位 `split/{N}.md` 中对应译文块并替换为 new_trans
- **缺译情况**（原文段后无译文块）：在原文段后插入 new_trans
- 生成 `split/{N}.fix.md` 修复记录

**JSON 容错（三段修复）**：verdicts 文件是 LLM 生成的 JSON，可能因值内含 ASCII 双引号/换行未转义而解析失败。脚本依次尝试：① 直接 json.load；② 按段落号键切分后对每个对象单独 json.loads；③ 字段级正则提取。某批次三种方式都失败时，该批段落标记为「批次解析失败」并在报告中列出。

**段落定位**：按段落号（与 check.md 同一序号体系）在 `split/{N}.md` 中定位原文段（非 `#`/`*` 开头的块），找到其后紧跟的译文块，整体替换。从后往前替换以避免行索引偏移。

**格式校验**：对 ACCEPT 的 new_trans 校验：以 `*` 开头且以 `*` 结尾、单行。校验失败的不应用。

报告格式（`{book}/split/{N}.fix.md`）：
```markdown
# 长阿含经卷3（chang/split/3.md）译文修复报告

- 修复时间：<日期>
- 校对问题数：X
- 成立并修复：Y（占 Z%）
- 不成立：A
- 校验失败：B
- 应用失败：C
- 批次解析失败：D

## 修复记录

### 段落 8 【近似未翻译】 ✅ 已修复
- **原文**：……
- **原译文**：……
- **校对问题**：……
- **修改建议**：……
- **判断依据**：……
- **新译文**：……

### 段落 99 【其它质量】 ❌ 不成立，未修复
- ……

## 汇总
……
```

## 步骤四：清理
删除临时文件：`{book}/split/fix_{N}_pairs.json`、`fix_{N}_batch*.json`、`fix_{N}_batch*.verdict.json`。

## 步骤五（可选）：校验

```
python3 .claude/skills/fix-ahan/verify_fix.py <book> <start> <end>
```
纯文本校验：fix.md 中每个「✅ 已修复」段落的新译文是否真的出现在 `{N}.md` 中、头部统计与正文一致。批量修复后建议跑一次。

# 大文件处理

- 每卷问题数由 `prepare_fix.py` 输出决定批次数量。
- 批次在卷内、以及多卷之间均可并行派发。
- 单卷批次较多时（>8），分批派发（如每轮 8 个）。

# 交互反馈

- 启动时，简要确认修复的经书与卷范围。
- 派发后保持静默高效。
- 完成后告知每卷的修复统计（成立 X 条 / 不成立 Y 条）。
- 结束时输出简明报告：修复卷数、应用修复总数、拒绝总数。
