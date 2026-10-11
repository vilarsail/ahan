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

  # 合并 0.md, 1.md, ... 为单一源文件（每文件以 h1 开头，pandoc 按其切分章节）
  merged="$workdir/merged.md"
  for f in $(ls "$dir/split" | grep -E '^[0-9]+\.md$' | sort -t. -k1 -n); do
    cat "$dir/split/$f" >> "$merged"
    printf '\n\n' >> "$merged"
  done
  echo "$book: 共 $(grep -c '^# ' "$merged") 章"

  epub="$dir/$title(2.0导读注释版).epub"
  pdf="$dir/$title(2.0导读注释版).pdf"
  if [ -f "$epub" ] && [ ! -f "$epub.bak" ]; then cp "$epub" "$epub.bak"; fi
  if [ -f "$pdf" ] && [ ! -f "$pdf.bak" ]; then cp "$pdf" "$pdf.bak"; fi

  pandoc "$merged" -o "$epub" \
    --metadata title="$title" \
    --metadata lang=zh-CN \
    --css="$ROOT/epub.css" \
    --epub-cover-image="$cover"

  ebook-convert "$epub" "$pdf" > /dev/null 2>&1
  echo "$book: 完成 $(du -h "$epub" "$pdf" | awk '{print $2" "$1}' | tr '\n' ' ')"
done
