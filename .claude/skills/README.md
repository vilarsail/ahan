# ahan skills — 四部阿含经 AI 流水线工具集

本目录下的 skills 把四部阿含经的翻译校对、修复、明晰化、导读注释、笔记、学习网页、思维导图、补译等工作流流水线化：**确定性脚本负责切分、定位、格式校验、报告生成与回写；LLM 只做语义判断（翻译、校对、改写、撰写）**。所有脚本从**项目根目录**运行。

## 四部经与目录结构

| 代号 | 经名 | 卷数 | 译者（底本时代） |
|------|------|------|------|
| `chang` | 长阿含经 | 22 | 后秦 佛陀耶舍/竺佛念 译 |
| `zhong` | 中阿含经 | 60 | 东晋 瞿昙僧伽提婆 译 |
| `za` | 杂阿含经 | 50 | 刘宋 求那跋陀罗 译 |
| `zengyi` | 增一阿含经 | 51 | 东晋 瞿昙僧伽提婆 译 |

四个子目录内部结构一致：

```
{book}/                      book ∈ chang | zhong | za | zengyi
├── origin/origin.txt        原始完整经文（大正藏底本，只读参考）
├── split/                   工作目录
│   ├── 0.md                 整理者前言（不参与任何流水线）
│   ├── {N}.md               第 N 卷正文（N ≥ 1）：原文段与单行 *译文* 段交替
│   ├── {N}.txt              第 N 卷原始原文（无译文，只读参考）
│   ├── {N}.check.md         校对报告（check-ahan）
│   ├── {N}.fix.md           修复记录（fix-ahan）
│   ├── {N}.smooth.md        明晰化报告（smooth-ahan）
│   ├── {N}.notes.md         词语注释表（read-ahan）
│   ├── {N}.guide.md         导读（read-ahan）
│   ├── {N}.summary.md       层级列表笔记（summarize-ahan）
│   └── *_*.json             各流水线临时文件
├── study/
│   ├── {N}-study.html       交互学习网页（study-ahan）
│   └── {N}-mindmap.html     思维导图（mindmap-ahan）
├── {经名}.epub / .pdf       成书
└── cover.jpg
```

### 正文格式（四部经统一，脚本解析的唯一依据）

- **空行分块**；标题块以 `#` 开头；译文块以 `*` 开头（**单行** `*...*`，多行颂偈的译文也合并为一行）；其余为原文块
- 原文块与译文块交替：每个原文块后紧跟其译文块
- **段落号 = 文件内原文块的顺序号**（标题不计入），check / fix / smooth / read / translate 各 skill 共用同一编号体系
- 多行颂偈算一个原文段（块内每行一句偈）

### 与 yoga 项目（.claude/skills/*-yoga）的差异

- yoga 是单本书、`output/{N}.md` 一个目录；本项目四部经各有 `{book}/split/`，所有脚本第一个参数都是 `<book>`
- yoga 原文段以全角缩进 `　　` 开头、译文可多行；本项目原文块无缩进前缀、译文一律单行——解析逻辑因此改为空行分块模型（共享库 `_lib/ahan_common.py`），颂偈行数校验已移除
- yoga 有 `split-origin`（把 origin 切分到 output）；本项目四部经均已切分完毕（split/{N}.txt + {N}.md 已存在），且 origin 为整部单文件，该 skill 不适用，故未移植

## Skill 一览与调用方式

调用格式统一为 `/skill名 <book> <start> <end>`（如 `/check-ahan za 1 10`）。脚本调用格式统一为 `python3 .claude/skills/<skill>/<脚本>.py <book> <N> [<M> ...]`（单卷或区间）。

| Skill | 用途 | 主要脚本 |
|-------|------|----------|
| **check-ahan** | 校对译文质量（近似未翻译/缺译/误译/格式），产出 `{N}.check.md` | prepare_check.py, build_report.py |
| **fix-ahan** | 按校对意见逐条判断并修复译文（含补译缺译段），产出 `{N}.fix.md` | prepare_fix.py, apply_fix.py, verify_fix.py |
| **smooth-ahan** | 明晰化「内容对但读不懂」的译文（两阶段：改写→忠实性校验→回退），产出 `{N}.smooth.md`；附术语盲点扫描 scan_terms.py 与统一整改 rewrite_terms.py | prepare/apply/finalize_smooth.py, advance_pipeline.py |
| **read-ahan** | 通读原文生成导读 `{N}.guide.md` + 词语注释 `{N}.notes.md`，圈号 ①② 自动写入 `{N}.md` 原文 | prepare_reading.py, build_reading.py, fix_circled.py |
| **summarize-ahan** | 把一卷概括为层级列表笔记 `{N}.summary.md`（思维导图的输入） | verify_summary.py |
| **mindmap-ahan** | 把 `{N}.summary.md` 确定性转换为幕布风格思维导图 `{book}/study/{N}-mindmap.html`（无 LLM） | build_mindmap.py |
| **study-ahan** | 生成单文件交互式学习网页 `{book}/study/{N}-study.html`（三件套概念卡+案例+交互组件） | check_study.py, template.html |
| **translate-ahan** | 补译缺译段 / 整卷重译（滑动窗口 + 并行子 Agent 批次） | split_paragraphs.py, merge_translations.py |

### 推荐流水线顺序

1. **校对**：`/check-ahan <book> <s> <e>` → 发现问题
2. **修复**：`/fix-ahan <book> <s> <e>` → 应用修复（先于 smooth，避免 fix 与 smooth 相互覆盖）
3. **明晰化**（可选）：`/smooth-ahan <book> <s> <e>` → 译文通顺化（自带二阶段校验）
4. **再次校对**：确认修复效果
5. **导读注释**：`/read-ahan <book> <s> <e>` → guide + notes + 圈号
6. **笔记与导图**：`/summarize-ahan <book> <s> <e>` → `/mindmap-ahan <book> <s> <e>`
7. **学习网页**：`/study-ahan <book> <s> <e>`

## 共享库

`_lib/ahan_common.py`：四部经元数据与卷号校验（BOOKS）、空行分块解析（block_spans/extract_pairs）、段落定位与译文替换/插入（locate/replace/insert_trans_block）、译文格式校验（validate_new_trans：单行 `*...*`）、LLM JSON 容错修复（load_json_repair）、圈号常量。各 skill 脚本通过相对路径 import，**移动 skill 目录时须保持 `_lib` 与各 skill 平级**。

## 注意事项

- 所有 `{N}.md` 的修改类流水线（fix/smooth/translate）从后往前替换、带格式校验与 JSON 容错；跑完可用 `verify_fix.py` 做纯文本核验。
- 临时文件（`pairs_/check_/issues_/fix_/smooth_/paragraphs_/translations_` 前缀 JSON）都在 `{book}/split/`，流水线结束即清理。
- git 提交前建议 `git diff {book}/split/{N}.md` 抽查回写结果；原文块应零改动（除 read-ahan 插入的圈号）。

## 并发经验值（实测）

- **子代理并发上限 L=3**：本环境中同时派发 3 个 `general-purpose` 子代理稳定成功；4 个及以上会立即返回 `user concurrency limit exceeded`（非 API 429，是平台侧并发闸门）。实测记录：7 并发→4 失败；4 并发→1 失败；3 并发→多次波次全部成功。
- **编排要点**：长任务（如 read-ahan 的导读生成约 4-8 分钟）放后台（`run_in_background`），短任务（check/fix 批次约 1-4 分钟）前台成对派发，凑满 3 路并发；所有批次文件必须**在派发前由当前版本数据生成**，流水线中途修改过 md 后务必重新跑 prepare 脚本，否则子代理会读到过期批次。
