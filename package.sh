#!/usr/bin/env bash
# 打包四部阿含经为 epub + pdf
# 用法: ./package.sh [book ...]   book: chang|zhong|za|zengyi，缺省打包全部
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

book_title() {
  case "$1" in
    chang)  echo 长阿含经 ;;
    zhong)  echo 中阿含经 ;;
    za)     echo 杂阿含经 ;;
    zengyi) echo 增一阿含经 ;;
    *)      echo "" ;;
  esac
}

BOOKS=("$@")
if [ ${#BOOKS[@]} -eq 0 ]; then
  BOOKS=(chang zhong za zengyi)
fi

for book in "${BOOKS[@]}"; do
  title="$(book_title "$book")"
  if [ -z "$title" ]; then
    echo "未知书籍: $book (可选: chang zhong za zengyi)" >&2
    exit 1
  fi
  dir="$ROOT/$book"
  [ -d "$dir/split" ] || { echo "缺少 $dir/split，跳过 $book" >&2; continue; }

  cover="$dir/cover.jpg"
  [ -f "$cover" ] || cover="$dir/cover.png"

  workdir="$(mktemp -d)"
  trap 'rm -rf "$workdir"' EXIT

  # 组装：每卷 = 卷标题 → 导读 → 正文（原文+译文，标注链至注释） → 词语注释（可跳回原文）
  merged="$workdir/merged.md"
  python3 - "$dir/split" "$merged" <<'PYEOF'
import re, sys, pathlib
split = pathlib.Path(sys.argv[1])
CIRC = {chr(c): c - 0x2460 + 1 for c in range(0x2460, 0x2474)}
CIRC.update({chr(c): c - 0x3251 + 21 for c in range(0x3251, 0x3260)})
CIRC.update({chr(c): c - 0x32B1 + 36 for c in range(0x32B1, 0x32C0)})
CIRC_RE = re.compile("[" + "".join(CIRC) + "]")

def esc(t):
    return (t.replace("\\", r"\\").replace("[", r"\[")
             .replace("]", r"\]").replace("*", r"\*"))

def note_terms(path):
    terms = {}
    for line in path.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"^(.)\s+(.+?)　", line)
        if m and m.group(1) in CIRC:
            terms[CIRC[m.group(1)]] = m.group(2)
    return terms

def link_text(text, vol, terms):
    """原文：标记连同左侧词条链接到注释条目，词条加下划线、编号转上标。"""
    seen, out, pos = set(), [], 0
    for m in CIRC_RE.finditer(text):
        idx = CIRC[m.group(0)]
        term = terms.get(idx)
        if term is None:
            continue
        start = m.start()
        tstart = start - len(term) if text.startswith(term, start - len(term)) else start
        out.append(text[pos:tstart])
        anchor = f'<a id="v{vol}t{idx}"></a>' if idx not in seen else ""
        seen.add(idx)
        if tstart < start:
            out.append(f'{anchor}[<u>{esc(term)}</u>^{idx}^](#v{vol}n{idx})')
        else:
            out.append(f'{anchor}[^{idx}^](#v{vol}n{idx})')
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)

def link_title(title, vol, terms):
    """标题行：标记保持原样，仅注入隐形锚点，避免污染目录样式。"""
    out, pos = [], 0
    for m in CIRC_RE.finditer(title):
        idx = CIRC[m.group(0)]
        if idx not in terms:
            continue
        out.append(title[pos:m.start()])
        out.append(f'<a id="v{vol}t{idx}"></a>')
        pos = m.start()
    out.append(title[pos:])
    return "".join(out)

def link_notes(text, vol):
    """注释：条目加锚点与「↩ 回原文」，条目之间插空行防止粘连。"""
    lines = []
    for line in text.split("\n"):
        m = re.match(r"^(.)(\s+)(.*)$", line)
        if m and m.group(1) in CIRC:
            idx = CIRC[m.group(1)]
            lines.append(f'<a id="v{vol}n{idx}"></a>{line}　[↩ 回原文](#v{vol}t{idx})')
            lines.append("")
        else:
            lines.append(line)
    return "\n".join(lines)

LIST_RE = re.compile(r"^(\s*)([-*]|\d+[.)])\s+")

def ensure_list_breaks(text):
    """列表行前若无空行，pandoc 会把它并入上一段落。自动补空行。"""
    lines, out, prev = text.split("\n"), [], ""
    for line in lines:
        if LIST_RE.match(line) and prev.strip() and not LIST_RE.match(prev):
            out.append("")
        out.append(line)
        prev = line
    return "\n".join(out)

def body_of(path):
    lines = path.read_text(encoding="utf-8").rstrip().split("\n")
    return "\n".join(l for l in lines if not l.startswith("# ")).strip()

nums = sorted(int(p.stem) for p in split.glob("[0-9]*.md")
              if re.match(r"^\d+\.md$", p.name) and p.name != "0.md")
parts = []
pre = split / "0.md"
if pre.exists():
    parts.append(pre.read_text(encoding="utf-8").rstrip())
for n in nums:
    main = (split / f"{n}.md").read_text(encoding="utf-8").rstrip().split("\n")
    terms = {}
    if (split / f"{n}.notes.md").exists():
        terms = note_terms(split / f"{n}.notes.md")
    body = link_text("\n".join(main[1:]).strip(), n, terms)
    chap = [link_title(main[0], n, terms), ""]
    g = split / f"{n}.guide.md"
    if g.exists():
        chap += ["## 导读", "",
                 re.sub(r"^(#+) ", r"\1# ",
                        ensure_list_breaks(body_of(g)), flags=re.M), ""]
    chap += [body, ""]
    nt = split / f"{n}.notes.md"
    if nt.exists():
        chap += ["## 词语注释", "", link_notes(body_of(nt), n), ""]
    parts.append("\n".join(chap))
out = sys.argv[2]
pathlib.Path(out).write_text("\n\n".join(parts) + "\n", encoding="utf-8")
print(f"{len(nums) + (1 if pre.exists() else 0)} 章")
PYEOF
  echo "$book: 共 $(grep -c '^# ' "$merged") 章"

  epub="$dir/$title(2.0导读注释版).epub"
  pdf="$dir/$title(2.0导读注释版).pdf"
  if [ -f "$epub" ] && [ ! -f "$epub.bak" ]; then cp "$epub" "$epub.bak"; fi
  if [ -f "$pdf" ] && [ ! -f "$pdf.bak" ]; then cp "$pdf" "$pdf.bak"; fi

  pandoc "$merged" -o "$epub" \
    --from=markdown-subscript \
    --metadata title="$title" \
    --metadata lang=zh-CN \
    --css="$ROOT/epub.css" \
    --toc-depth=2 \
    --epub-cover-image="$cover"

  ebook-convert "$epub" "$pdf" > /dev/null 2>&1
  echo "$book: 完成 $(du -h "$epub" "$pdf" | awk '{print $2" "$1}' | tr '\n' ' ')"
done
