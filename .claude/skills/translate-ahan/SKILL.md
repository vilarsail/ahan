---
name: translate-ahan
description: 批量且高精度翻译四部阿含经（chang/zhong/za/zengyi）的文言原文（{book}/split/{N}.md），用于补译缺译段或重译指定卷。超过20段的大文件自动拆分为每20段一个批次，通过并行子Agent独立翻译，避免上下文衰减。应用滑动窗口机制（每次5段，参考前2段上下文）确保语义连贯及佛教名词一致。原文与译文通过确定性脚本分合，LLM 只做翻译。当用户输入 /translate-ahan <book> <start> <end> 或要求"补译/重译第 X-Y 卷"时触发。
---

# 角色与目标

你是一个专门用于古文佛典翻译的自动化 Agent。任务是对 `{book}/split/{N}.md`（`{book}` ∈ `chang`（长阿含经，22卷）/ `zhong`（中阿含经，60卷）/ `za`（杂阿含经，50卷）/ `zengyi`（增一阿含经，51卷））中的原文段进行翻译：**已有译文的段落重译替换，缺译的段落补译插入**。

适用场景：
1. 校对发现整卷大面积 NEAR-COPY / ERROR，需要整卷重译；
2. 卷中存在 MISSING（缺译）段落，需要补译（先用 `/check-ahan` 找出缺译段）。

# 项目目录结构

```
{book}/
    origin/origin.txt   原始完整经文（大正藏底本，只读参考）
    split/
        0.md            整理者前言（不参与）
        {N}.md          第 N 卷正文（原文段与单行 *译文* 段交替）——翻译产物写回此文件
        {N}.txt         第 N 卷原始原文（无译文，只读参考）
        paragraphs_{N}.json / translations_{N}.json / *_batch*.json   临时文件
```

**正文格式（四部经统一）**：空行分块；标题行以 `#` 开头；译文行以 `*` 开头（**单行** `*...*`）；其余为原文段。段落号 = 文件内原文段的顺序号（标题不计入）。多行颂偈算一个原文段，其译文合并为一行。

**已有圈号标注（read-ahan 产物）**：原文段内可能含有 ① ② 圈号。merge 脚本只替换/插入译文块，原文块（含圈号）100% 保留，不受影响。

# 架构设计（重要）

**原文永不进入 LLM 写入路径。** 拆段和合并由确定性脚本完成，LLM 只负责翻译。

```
split_paragraphs.py  →  {book}/split/paragraphs_{N}.json  →  [LLM 翻译]  →  {book}/split/translations_{N}.json  →  merge_translations.py  →  {book}/split/{N}.md
```

- `split_paragraphs.py`：从 `split/{N}.md` 提取原文段 → JSON
- LLM：读 JSON，滑动窗口翻译，写 JSON
- `merge_translations.py`：读译文 JSON → 已有译文块替换、缺译块插入 → 覆写 `split/{N}.md`

# 核心翻译原则
1. **信达雅与专业性**：准确理解句读逻辑，将古文转换为现代白话文，精准保留佛教核心名词（比丘、涅槃、五蕴、四圣谛、十二因缘等），人名地名保持原样并前后一致。
2. **免译清单**：**绝对不要翻译任何标题**（`#`/`##` 开头的行）。标题不参与分块、不翻译。
3. **格式要求**：所有译文必须以**斜体**（`*翻译内容*`）格式化，**必须单行**（多行颂偈译文也合并为一行），**仅包含译文本身，不得添加任何前缀标记**。
4. **逐段对照**：段落号与 `paragraphs_{N}.json` 严格对应。

# 自动化执行工作流 (Workflow)

## 步骤一：拆段（确定性脚本）
```
python3 .claude/skills/translate-ahan/split_paragraphs.py <book> <N>
```
生成 `{book}/split/paragraphs_{N}.json`，格式为 `{"1": "原文段落1", "2": "原文段落2\n多行", ...}`。

## 步骤二：滑动窗口翻译（LLM 核心工作）
读取 `paragraphs_{N}.json`，按段落顺序，将**每 5 个段落**划分为一个翻译块（Chunk）。

- 最后一个 Chunk 不足 5 段也单独成块。

依次对每个 Chunk 进行翻译，遵循"滑动窗口"机制：
- **引入上下文**：提取当前 Chunk 前方的 2 个段落作为语境参考（**不翻译**，仅参考），以防断章取义造成的幻觉或漏译。
- **翻译目标**：将当前的 5 个段落进行翻译，保持段落数量一一对应。
- **输出要求**：单行 `*译文*`；颂偈真正翻译为通顺白话；不得添加前缀。

## 步骤三：累积写入 translations_{N}.json
每翻译完一个 Chunk，将译文以 **JSON 追加**方式写入 `{book}/split/translations_{N}.json`。最终文件格式：
```json
{
  "1": "*译文段落1*",
  "2": "*译文段落2*",
  "3": "*译文段落3*"
}
```

## 步骤四：合并（确定性脚本）
```
python3 .claude/skills/translate-ahan/merge_translations.py <book> <N>
```
逐段把译文写回 `split/{N}.md`：原文块后有译文块则整体替换，无则插入。

**要点**：
- 原文与译文之间不加分割线，中间仅空行
- 标题行后不加译文
- 原文 100% 由脚本保留（含已有圈号标注），无需 LLM 校验

## 步骤五：清理
翻译成功后，删除 `{book}/split/paragraphs_{N}.json`、`translations_{N}.json`（及批次临时文件）。

# 大文件分批机制（关键）

**问题**：当单个文件段落数超过约 20 段时，LLM 在单次会话中处理全部段落会出现**上下文注意力衰减**：前半部分翻译质量正常，后半部分逐渐退化为仅做标点替换。za/zengyi/zhong 单卷可达 100-300+ 段，必须分批处理。

**机制**：以 **每 20 段为一个批次**，使用 Task 工具将每个批次派发给独立的子 Agent，**所有批次并行执行**。

## 执行流程

### 步骤 2.0：判断是否需要分批
1. 运行 `split_paragraphs.py <book> <N>` 得到总段落数 `P`
2. 若 `P <= 20`：在当前会话中一次性处理
3. 若 `P > 20`：执行分批流程

### 步骤 2.1：生成批次文件
```bash
python3 -c "
import json
book, N = '<book>', '<N>'
data = json.load(open(f'{book}/split/paragraphs_{N}.json'))
P = len(data)
batch_size = 20
batch_num = 0
for start in range(1, P + 1, batch_size):
    batch_num += 1
    end = min(start + batch_size - 1, P)
    batch = {}
    ctx_start = max(1, start - 2)
    if start > 1:
        batch['_context_keys'] = [str(i) for i in range(ctx_start, start)]
        for i in range(ctx_start, start):
            batch[f'_context_{i}'] = data[str(i)]
    batch['_target_keys'] = [str(i) for i in range(start, end + 1)]
    for i in range(start, end + 1):
        batch[str(i)] = data[str(i)]
    batch['_start'] = start
    batch['_end'] = end
    batch['_batch'] = batch_num
    batch['_total_batches'] = (P + batch_size - 1) // batch_size
    json.dump(batch, open(f'{book}/split/paragraphs_{N}_batch{batch_num}.json', 'w'), ensure_ascii=False, indent=2)
    print(f'Batch {batch_num}: paragraphs {start}-{end}')
"
```

### 步骤 2.2：并行派发子 Agent
**关键**：所有批次必须在**同一轮消息中并行派发**。子 Agent prompt 精简（指令在 AGENT_INSTRUCTIONS.md，子 Agent Read 一次即可）：

```
读取 .claude/skills/translate-ahan/AGENT_INSTRUCTIONS.md 获取翻译指令，按其要求翻译。

批次文件：{book}/split/paragraphs_{N}_batch{batch_num}.json
输出文件：{book}/split/translations_{N}_batch{batch_num}.json
```

### 步骤 2.3：合并批次 + 过滤元数据 + 格式修复 + 未翻译检查
所有子 Agent 完成后：

```bash
python3 -c "
import json, re, difflib, os
book, N = '<book>', '<N>'
outdir = f'{book}/split'
merged = {}
batch_num = 1
batches_found = 0
while True:
    path = f'{outdir}/translations_{N}_batch{batch_num}.json'
    if not os.path.exists(path):
        break
    batch = json.load(open(path))
    for key, value in batch.items():
        if key.startswith('_'):
            continue
        merged[key] = value
    batches_found = batch_num
    batch_num += 1
if batches_found == 0:
    print('ERROR: 未找到任何批次文件')
    exit(1)
original = dict(merged)
fixed = 0
for key, value in merged.items():
    if not isinstance(value, str):
        print(f'WARNING: paragraph {key} value is not string')
        continue
    value = re.sub(r'^\*(译文|翻译|译)\*\s*', '*', value)
    # 合并为单行（阿含正文格式）
    value = value.replace(chr(10), '')
    if value and not value.startswith('*'):
        value = '*' + value
    if value and not value.endswith('*'):
        value = value + '*'
    merged[key] = value
    if value != original[key]:
        fixed += 1
json.dump(merged, open(f'{outdir}/translations_{N}.json', 'w'), ensure_ascii=False, indent=2)
print(f'Merged {batches_found} batches -> {len(merged)} translations, {fixed} entries fixed')
paragraphs = json.load(open(f'{outdir}/paragraphs_{N}.json'))
warnings = 0
for key, value in merged.items():
    if key in paragraphs and isinstance(value, str):
        orig = paragraphs[key].replace('　　', '').replace('。', '').replace('，', '').replace(' ', '')
        trans = value.replace('*', '').replace('。', '').replace('，', '').replace(' ', '')
        ratio = difflib.SequenceMatcher(None, orig, trans).ratio()
        if ratio > 0.8 and len(orig) > 20:
            print(f'WARNING: paragraph {key} may not be translated (similarity {ratio:.1%})')
            warnings += 1
if warnings:
    print(f'Total untranslated warnings: {warnings}')
"
```

修复后，人工检查 WARNING 提示的段落，确认是否需要重新翻译。

### 步骤 2.4：继续执行步骤四和步骤五
合并完成后，继续执行步骤四（`merge_translations.py`）和步骤五（清理，包括所有批次临时文件）。

## 注意事项
- **并行是关键**：所有子 Agent 必须在同一轮消息中派发，不要顺序处理
- 每个子 Agent 有独立上下文，不会出现注意力衰减
- 上下文段落（`_context_*`）仅用于帮助子 Agent 理解语义连续性，不翻译、不输出

# 交互反馈
- 启动时，简要向用户确认将要处理的经书与卷范围。
- 检测到段落数 > 20 时，告知用户将拆分为 N 个批次、派发 N 个并行子 Agent。
- 任务结束时，输出一份简明的处理报告。
