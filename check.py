import re
import argparse
from collections import defaultdict

def classify_char(ch):
    code = ord(ch)

    if 0xE000 <= code <= 0xF8FF:
        return "PUA(私有区-疑似CBETA缺字)"
    elif code >= 0x20000:
        return "Unicode扩展区"
    elif ch == "�":
        return "乱码替换符"
    elif code < 32 and ch not in ['\n', '\t']:
        return "控制字符"
    elif '\u2FF0' <= ch <= '\u2FFF':
        return "组合字结构符"
    else:
        return None


def analyze_text(text, context_window=10):
    stats = defaultdict(lambda: {
        "count": 0,
        "type": "",
        "examples": []
    })

    for i, ch in enumerate(text):
        category = classify_char(ch)
        if category:
            key = f"{ch} (U+{ord(ch):04X})"

            stats[key]["count"] += 1
            stats[key]["type"] = category

            if len(stats[key]["examples"]) < 3:
                start = max(0, i - context_window)
                end = min(len(text), i + context_window)
                snippet = text[start:end].replace("\n", "\\n")
                stats[key]["examples"].append(snippet)

    return stats


def print_report(stats):
    print("=== 异常字符检测报告 ===\n")

    for ch, info in stats.items():
        print(f"字符: {ch}")
        print(f"类型: {info['type']}")
        print(f"出现次数: {info['count']}")
        print("示例上下文:")
        for ex in info["examples"]:
            print(f"  - {ex}")
        print("-" * 40)


def analyze_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    stats = analyze_text(text)
    print_report(stats)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="检测文本中的CBETA异常字符")
    parser.add_argument("file", help="输入的txt文件路径")

    args = parser.parse_args()

    analyze_file(args.file)
